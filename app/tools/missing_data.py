"""Data quality checker using validation evidence."""
from app.services.validation import ToolResult, ValidatedData


def check_missing(data: ValidatedData) -> ToolResult:
    """Report missing and invalid fields with source-row references."""
    return ToolResult(tool='missing_data', findings=data.issues,
        metrics={'issue_count': len(data.issues),
                 'affected_rows': len({r for f in data.issues for r in f.rows}),
                 'excluded_rows': int((~data.cleaned['eligible']).sum())})
