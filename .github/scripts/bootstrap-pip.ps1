$ErrorActionPreference = 'Stop'

# Official eMudhra / emSign recovery wheel; verify its hash before executing it.
# https://www.python.org/downloads/release/python-3149/
python --version
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to determine Python version'
}
python -m pip --disable-pip-version-check install --no-deps --no-cache-dir --force-reinstall 'pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70'
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to install the hash-verified pip wheel'
}
python "$PSScriptRoot/verify-python-security.py"
if ($LASTEXITCODE -ne 0) {
    throw 'Python packaging security verification failed'
}
