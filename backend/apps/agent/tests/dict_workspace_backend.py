from dataclasses import dataclass, field

from deepagents.backends.protocol import EditResult, ReadResult, WriteResult


@dataclass
class DictWorkspaceBackend:
    files: dict[str, str] = field(default_factory=dict)
    reject_overwrite_on_write: bool = False

    def read(self, path: str) -> ReadResult:
        if path not in self.files:
            return ReadResult(error="file_not_found")
        return ReadResult(file_data={"content": self.files[path], "encoding": "utf-8"})

    def write(self, path: str, content: str) -> WriteResult:
        if self.reject_overwrite_on_write and path in self.files:
            return WriteResult(
                error=(
                    f"Cannot write to {path} because it already exists. "
                    "Read and then make an edit, or write to a new path."
                )
            )
        self.files[path] = content
        return WriteResult(path=path)

    def edit(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        if path not in self.files:
            return EditResult(error=f"Error: File '{path}' not found")
        content = self.files[path]
        if old_string not in content:
            return EditResult(error="Error: Old string not found in file")
        if replace_all:
            occurrences = content.count(old_string)
            self.files[path] = content.replace(old_string, new_string)
        else:
            occurrences = 1
            self.files[path] = content.replace(old_string, new_string, 1)
        return EditResult(path=path, occurrences=occurrences)
