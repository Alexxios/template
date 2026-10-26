{% raw %}from {{cookiecutter.package_name}} import __version__


def test_package_version():
    assert __version__ == "{{cookiecutter.version}}"
{% endraw %}