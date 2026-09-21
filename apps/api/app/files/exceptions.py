class FileStorageError(ValueError):
    pass


class UnsafeFileNameError(FileStorageError):
    pass


class UnsupportedFileTypeError(FileStorageError):
    pass


class FileReferenceError(FileStorageError):
    pass


class PersistentStorageError(FileStorageError):
    pass


class RemoteObjectNotFoundError(PersistentStorageError):
    pass


class BackupIntegrityError(ValueError):
    pass
