from {{cookiecutter.package_name}} import __version__


def test_{{cookiecutter.package_name}}_version():
    assert __version__ == "{{cookiecutter.version}}"
