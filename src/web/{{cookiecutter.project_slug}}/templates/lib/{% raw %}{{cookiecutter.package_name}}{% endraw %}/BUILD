python_sources(
    name="member",
    sources=["**/*.py", "**/*.pyi"],
    dependencies=[":files", "//:ci"],
)

files(
    name="files",
    sources=["**/*", "!**/*.py", "!**/*.pyi", "!BUILD"],
)
