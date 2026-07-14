class FileStorageError(ValueError):
    pass


class UnsafeFileNameError(FileStorageError):
    pass


class UnsupportedFileTypeError(FileStorageError):
    pass


class FileReferenceError(FileStorageError):
    pass


class BackupIntegrityError(ValueError):
    pass
