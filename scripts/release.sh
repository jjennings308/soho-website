#!/usr/bin/env bash
#
# Release `dev` to production: verify, fast-forward `main` to `dev`, push,
# and optionally run the deploy on the VPS.
#
# Run locally from anywhere in the repo:
#     scripts/release.sh                 # checks + push main; prints the VPS command
#     scripts/release.sh --deploy        # ...then runs scripts/deploy.sh on the VPS over SSH
#     scripts/release.sh --skip-tests    # skip the test suite (e.g. test DB unavailable)
#
# Checks before anything is pushed:
#   - on `dev`, and `dev` is not behind origin/dev
#   - origin/main fast-forwards to `dev` (never rewrites main)
#   - no model changes missing a migration
#   - static/dist/output.css matches a fresh Tailwind build (the VPS doesn't build CSS)
#   - the test suite passes
#
# Uncommitted changes are never released — only committed work on `dev`.
#
# Environment:
#     SOHO_SSH   SSH target for --deploy, e.g. james@209.46.125.163

set -euo pipefail

VPS_DEPLOY=/var/www/soho/scripts/deploy.sh

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

main() {
    local deploy=false skip_tests=false
    for arg in "$@"; do
        case "$arg" in
            --deploy)     deploy=true ;;
            --skip-tests) skip_tests=true ;;
            *) die "Unknown option: $arg (usage: release.sh [--deploy] [--skip-tests])" ;;
        esac
    done
    if $deploy && [[ -z ${SOHO_SSH:-} ]]; then
        die "--deploy needs SOHO_SSH set, e.g. SOHO_SSH=james@209.46.125.163"
    fi

    cd "$(git rev-parse --show-toplevel)"
    export DJANGO_SETTINGS_MODULE=config.settings.development

    step "Checking branches"
    [[ $(git rev-parse --abbrev-ref HEAD) == dev ]] || die "Switch to the dev branch first."
    git fetch --quiet origin
    git merge-base --is-ancestor origin/dev dev \
        || die "Local dev is behind origin/dev — pull first."
    git merge-base --is-ancestor origin/main dev \
        || die "origin/main has commits that aren't on dev — merge main into dev first."

    local commits
    commits=$(git --no-pager log --oneline origin/main..dev)
    [[ -n $commits ]] || die "Nothing to release: origin/main already matches dev."

    local dirty
    dirty=$(git status --porcelain --untracked-files=no)
    if [[ -n $dirty ]]; then
        echo "Note: these uncommitted changes will NOT be released:"
        echo "$dirty"
    fi

    step "Checking for missing migrations"
    python manage.py makemigrations --check --dry-run >/dev/null \
        || die "Model changes without migrations — run makemigrations and commit."

    step "Checking Tailwind build is committed"
    if command -v npm >/dev/null && [[ -d node_modules ]]; then
        git diff --quiet -- static/dist/output.css \
            || die "static/dist/output.css has uncommitted changes — commit or discard them first."
        npm run --silent build >/dev/null 2>&1 || die "npm run build failed."
        if ! git diff --quiet -- static/dist/output.css; then
            die "static/dist/output.css was out of date. A fresh build is now in your working tree — review and commit it, then re-run."
        fi
    else
        echo "npm/node_modules not available — skipping (make sure output.css is current)."
    fi

    if $skip_tests; then
        step "Skipping tests (--skip-tests)"
    else
        step "Running tests"
        python manage.py test --noinput || die "Tests failed."
    fi

    step "Ready to release to production"
    echo "$commits"
    echo
    read -r -p "Push these commits to main? [y/N] " answer
    [[ $answer == [yY] ]] || die "Aborted — nothing pushed."

    step "Pushing"
    git push --quiet origin dev
    git push --quiet origin dev:main
    echo "origin/main is now $(git rev-parse --short dev)."

    if $deploy; then
        step "Deploying on $SOHO_SSH"
        ssh -t "$SOHO_SSH" "$VPS_DEPLOY"
    else
        echo
        echo "To deploy, run on the VPS:  $VPS_DEPLOY"
    fi
}

main "$@"
