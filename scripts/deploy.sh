#!/usr/bin/env bash
#
# Deploy the latest `main` on the production VPS.
#
# Run on the VPS as your normal (sudo-capable) login user:
#     /var/www/soho/scripts/deploy.sh            # deploy if origin/main has new commits
#     /var/www/soho/scripts/deploy.sh --force    # re-run every step even if up to date
#
# Steps: pull (fast-forward only) → pip install if requirements changed →
# Django deploy checks → migrate → createcachetable → collectstatic →
# restart soho.service → health check. Every deploy is logged to
# logs/deploy.log.
#
# Rollback is deliberately manual (the failure message prints the exact
# commands), because migrations that already ran may need reversing by hand.
#
# Environment overrides:
#     SOHO_HEALTH_URL   URL that must return 2xx/3xx after restart. Defaults to
#                       gunicorn directly (http://127.0.0.1:8000/), bypassing nginx
#                       and its staff-preview basic auth, which would return 401.
#     SOHO_HEALTH_HOST  Host header sent with the health check; must be in
#                       ALLOWED_HOSTS (default soho.tazcomputer.com)

set -Eeuo pipefail  # -E: the ERR trap also fires inside helper functions

APP_DIR=/var/www/soho
APP_USER=www-data
SERVICE=soho.service
BRANCH=main
PYTHON="$APP_DIR/.venv/bin/python"
PIP="$APP_DIR/.venv/bin/pip"
REQUIREMENTS=requirements/production.txt
HEALTH_URL="${SOHO_HEALTH_URL:-http://127.0.0.1:8000/}"
HEALTH_HOST="${SOHO_HEALTH_HOST:-soho.tazcomputer.com}"
LOG_FILE="$APP_DIR/logs/deploy.log"
LOCK_FILE=/tmp/soho-deploy.lock

PREV_COMMIT=""
NEW_COMMIT=""

as_app() { sudo -u "$APP_USER" "$@"; }
manage() { as_app "$PYTHON" manage.py "$@"; }
step()   { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die()    { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

log_result() {
    local status=$1
    printf '%s  %-8s  %s  %s -> %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$status" "${SUDO_USER:-$USER}" \
        "${PREV_COMMIT:0:7}" "${NEW_COMMIT:0:7}" \
        | as_app tee -a "$LOG_FILE" >/dev/null || true
}

# Once the checkout has moved, any failure prints how to get back.
on_failure() {
    log_result FAILED
    if [[ -n $PREV_COMMIT && $PREV_COMMIT != "$NEW_COMMIT" ]]; then
        cat >&2 <<EOF

Deploy FAILED after the code was updated (${PREV_COMMIT:0:7} -> ${NEW_COMMIT:0:7}).

To roll back the code:
    cd $APP_DIR
    sudo -u $APP_USER git reset --hard $PREV_COMMIT
    sudo systemctl restart $SERVICE

If migrations ran in this deploy, reverse them first (while still on the new
code) with:  sudo -u $APP_USER $PYTHON manage.py migrate <app> <previous_migration>
EOF
    fi
}

# Everything lives in main() so bash parses the whole script before running
# it — `git pull` may rewrite this file mid-deploy. Changes to this script
# take effect on the next run.
main() {
    local force=false
    case "${1:-}" in
        --force) force=true ;;
        "") ;;
        *) die "Unknown option: $1 (usage: deploy.sh [--force])" ;;
    esac

    cd "$APP_DIR"

    exec 9>"$LOCK_FILE"
    flock -n 9 || die "Another deploy is already running."

    step "Checking server checkout"
    local branch
    branch=$(as_app git rev-parse --abbrev-ref HEAD)
    [[ $branch == "$BRANCH" ]] || die "Server is on branch '$branch', expected '$BRANCH'."

    # staticfiles/ is still tracked in git but rewritten by collectstatic, so ignore it.
    local dirty
    dirty=$(as_app git status --porcelain --untracked-files=no -- . ':!staticfiles')
    [[ -z $dirty ]] || die "Server has uncommitted changes — resolve before deploying:
$dirty"

    step "Fetching origin/$BRANCH"
    as_app git fetch --quiet origin "$BRANCH"
    PREV_COMMIT=$(as_app git rev-parse HEAD)
    NEW_COMMIT=$(as_app git rev-parse "origin/$BRANCH")

    if [[ $PREV_COMMIT == "$NEW_COMMIT" ]]; then
        if ! $force; then
            echo "Already up to date at ${PREV_COMMIT:0:7}. Use --force to re-run all steps."
            exit 0
        fi
        echo "Already at ${PREV_COMMIT:0:7} — re-running steps (--force)."
    else
        as_app git merge-base --is-ancestor HEAD "origin/$BRANCH" \
            || die "origin/$BRANCH is not a fast-forward of the server checkout. Investigate manually."
        echo "Incoming commits:"
        as_app git --no-pager log --oneline "HEAD..origin/$BRANCH"
    fi

    trap on_failure ERR

    step "Updating code"
    # Older commits tracked staticfiles/, which collectstatic rewrites. Discard
    # any such edits so the merge can't be blocked; collectstatic regenerates
    # them below. (No-op once staticfiles/ is untracked.)
    as_app git checkout -- staticfiles 2>/dev/null || true
    as_app git merge --ff-only --quiet "origin/$BRANCH"

    if $force || ! as_app git diff --quiet "$PREV_COMMIT" "$NEW_COMMIT" -- requirements/; then
        step "Installing requirements ($REQUIREMENTS)"
        # --no-cache-dir: www-data cannot write /var/www/.cache
        as_app "$PIP" install --quiet --no-cache-dir -r "$REQUIREMENTS"
    else
        echo "Requirements unchanged — skipping pip install."
    fi

    step "Running Django deploy checks"
    manage check --deploy --fail-level ERROR

    step "Applying migrations"
    manage migrate --noinput

    step "Ensuring cache table exists"
    manage createcachetable

    step "Collecting static files"
    manage collectstatic --noinput

    step "Restarting $SERVICE"
    sudo systemctl restart "$SERVICE"
    sleep 3
    systemctl is-active --quiet "$SERVICE" \
        || { sudo systemctl status "$SERVICE" --no-pager -n 20 || true; false; }

    step "Health check: $HEALTH_URL (Host: $HEALTH_HOST)"
    local code=""
    for _ in 1 2 3 4 5; do
        # X-Forwarded-Proto mimics nginx so Django treats the request as https.
        code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
            -H "Host: $HEALTH_HOST" -H "X-Forwarded-Proto: https" "$HEALTH_URL" || true)
        [[ $code =~ ^[23] ]] && break
        sleep 2
    done
    [[ $code =~ ^[23] ]] || { echo "Health check returned HTTP ${code:-no response}" >&2; false; }
    echo "HTTP $code"

    trap - ERR
    log_result OK
    printf '\n\033[32m✓ Deployed %s\033[0m (%s)\n' \
        "$(as_app git --no-pager log -1 --format='%h %s')" "$(cat VERSION)"
}

main "$@"
