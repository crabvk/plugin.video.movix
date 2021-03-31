import pytest


def pytest_addoption(parser):
    parser.addoption('--credentials')


@pytest.fixture(scope='session')
def credentials(request):
    creds = request.config.option.credentials
    if creds is None:
        pytest.skip()
    return creds
