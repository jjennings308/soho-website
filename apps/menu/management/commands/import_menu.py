from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.menu.importers import KIND_ORDER, ImportRefused, apply, parse, read_csv_bytes


class Command(BaseCommand):
    help = (
        'Import one menu CSV. Without --apply this is a dry run that prints '
        'what would change. Kinds, in dependency order: ' + ', '.join(KIND_ORDER)
    )

    def add_arguments(self, parser):
        parser.add_argument('kind', choices=KIND_ORDER)
        parser.add_argument('file')
        parser.add_argument('--apply', action='store_true', help='Save the changes (all rows or none).')

    def handle(self, *args, kind, file, **options):
        path = Path(file)
        if not path.is_file():
            raise CommandError(f'No such file: {path}')
        text = read_csv_bytes(path.read_bytes())

        if options['apply']:
            try:
                result = apply(kind, text)
            except ImportRefused as exc:
                self._report(exc.result)
                raise CommandError('Nothing was saved — fix the errors above and run again.')
            self._report(result)
            self.stdout.write(self.style.SUCCESS(
                f"Saved: {result.count('new')} new, {result.count('update')} updated."))
            return

        result = parse(kind, text)
        self._report(result)
        if not result.ok:
            raise CommandError('The file has errors; nothing would be saved.')
        self.stdout.write(self.style.WARNING('Dry run — nothing saved. Re-run with --apply to save.'))

    def _report(self, result):
        for err in result.errors:
            self.stdout.write(self.style.ERROR(f'File: {err}'))
        for row in result.rows:
            if row.action == 'unchanged':
                continue
            style = self.style.ERROR if row.action == 'error' else (lambda s: s)
            self.stdout.write(style(f'line {row.line:>4}  {row.action.upper():<8} {row.label}'))
            for col, (old, new) in row.changes.items():
                if row.action == 'update':
                    self.stdout.write(f'            {col}: {_short(old)} → {_short(new)}')
            for note in row.notes:
                self.stdout.write(self.style.WARNING(f'            note: {note}'))
            for err in row.errors:
                self.stdout.write(self.style.ERROR(f'            {err}'))
        self.stdout.write(
            f"{result.kind}: {result.count('new')} new, {result.count('update')} to update, "
            f"{result.count('unchanged')} unchanged, {result.count('error')} with errors.")


def _short(value, limit=60):
    value = (value or '∅').replace('\n', ' ⏎ ')
    return value if len(value) <= limit else value[:limit - 1] + '…'
