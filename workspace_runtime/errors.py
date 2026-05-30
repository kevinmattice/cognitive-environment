class WorkspaceError(RuntimeError):
    pass


class ManifestError(WorkspaceError):
    pass


class SourceError(WorkspaceError):
    pass

