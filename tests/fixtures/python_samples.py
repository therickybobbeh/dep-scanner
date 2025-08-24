"""
Test fixtures for Python dependency files
"""

# Basic requirements.txt
BASIC_REQUIREMENTS_TXT = """
Flask==2.3.2
requests>=2.28.0
numpy~=1.24.0
click==8.1.3
werkzeug==2.3.6
"""

# Complex requirements.txt with various formats
COMPLEX_REQUIREMENTS_TXT = """
# Production dependencies
Django==4.2.1
psycopg2-binary>=2.9.0
redis>=4.0.0,<5.0.0
celery[redis]==5.2.7

# Development tools
pytest>=7.0.0
black==23.3.0
isort>=5.12.0
mypy==1.3.0

# Git dependency
git+https://github.com/user/repo.git@v1.0.0#egg=custom-package

# Local development
-e ./local-package

# Comments and empty lines

# Constraints
urllib3>=1.26.0,<2.0.0
"""

# Basic poetry.lock content (simplified TOML)
BASIC_POETRY_LOCK = """
[[package]]
name = "flask"
version = "2.3.2"
description = "A simple framework for building complex web applications."
category = "main"
optional = false
python-versions = ">=3.8"

[package.dependencies]
click = ">=8.1.3"
werkzeug = ">=2.3.3"
itsdangerous = ">=2.1.2"
jinja2 = ">=3.1.2"

[[package]]
name = "click"
version = "8.1.3"
description = "Composable command line interface toolkit"
category = "main"
optional = false
python-versions = ">=3.7"

[[package]]
name = "werkzeug"
version = "2.3.6"
description = "The comprehensive WSGI web application library."
category = "main"
optional = false
python-versions = ">=3.8"

[[package]]
name = "itsdangerous"
version = "2.1.2"
description = "Safely pass data to untrusted environments and back."
category = "main"
optional = false
python-versions = ">=3.7"

[[package]]
name = "jinja2"
version = "3.1.2"
description = "A very fast and expressive template engine."
category = "main"
optional = false
python-versions = ">=3.7"

[package.dependencies]
markupsafe = ">=2.0"

[[package]]
name = "markupsafe"
version = "2.1.3"
description = "Safely add untrusted strings to HTML/XML markup."
category = "main"
optional = false
python-versions = ">=3.7"

[[package]]
name = "pytest"
version = "7.4.0"
description = "pytest: simple powerful testing with Python"
category = "dev"
optional = false
python-versions = ">=3.7"

[package.dependencies]
pluggy = ">=0.12,<2.0"
packaging = "*"

[[package]]
name = "pluggy"
version = "1.2.0"
description = "plugin and hook calling mechanisms for python"
category = "dev"
optional = false
python-versions = ">=3.7"

[[package]]
name = "packaging"
version = "23.1"
description = "Core utilities for Python packages"
category = "dev"
optional = false
python-versions = ">=3.7"

[metadata]
lock-version = "2.0"
python-versions = "^3.8"
content-hash = "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
"""

# pyproject.toml (PEP 621 format)
BASIC_PYPROJECT_TOML = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "example-app"
version = "1.0.0"
description = "An example Python application"
authors = [{name = "Author", email = "author@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.8"
dependencies = [
    "flask>=2.3.0",
    "requests>=2.28.0",
    "click>=8.1.0",
    "numpy~=1.24.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "isort>=5.12.0"
]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0"
]
"""

# pyproject.toml (Poetry format)
POETRY_PYPROJECT_TOML = """
[tool.poetry]
name = "poetry-app"
version = "0.1.0"
description = "A Poetry-managed Python application"
authors = ["Author <author@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.8"
flask = "^2.3.2"
requests = "^2.28.0"
numpy = "~1.24.0"
click = ">=8.1.3"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.3.0"
isort = "^5.12.0"
mypy = "^1.3.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""

# Pipfile
BASIC_PIPFILE = """
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
django = ">=4.2.0"
psycopg2-binary = "*"
redis = ">=4.0.0,<5.0.0"
celery = {extras = ["redis"], version = ">=5.2.0"}
requests = "~=2.28.0"

[dev-packages]
pytest = "*"
black = "*"
isort = "*"
flake8 = "*"

[requires]
python_version = "3.8"
"""

# Pipfile.lock (simplified)
BASIC_PIPFILE_LOCK = """
{
    "_meta": {
        "hash": {
            "sha256": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
        },
        "pipfile-spec": 6,
        "requires": {
            "python_version": "3.8"
        },
        "sources": [
            {
                "name": "pypi",
                "url": "https://pypi.org/simple",
                "verify_ssl": true
            }
        ]
    },
    "default": {
        "django": {
            "hashes": [
                "sha256:abc123",
                "sha256:def456"
            ],
            "index": "pypi",
            "version": "==4.2.1"
        },
        "psycopg2-binary": {
            "hashes": [
                "sha256:ghi789"
            ],
            "index": "pypi",
            "version": "==2.9.6"
        },
        "redis": {
            "hashes": [
                "sha256:jkl012"
            ],
            "index": "pypi",
            "version": "==4.5.5"
        },
        "celery": {
            "hashes": [
                "sha256:mno345"
            ],
            "extras": ["redis"],
            "index": "pypi",
            "version": "==5.2.7"
        },
        "requests": {
            "hashes": [
                "sha256:pqr678"
            ],
            "index": "pypi",
            "version": "==2.31.0"
        }
    },
    "develop": {
        "pytest": {
            "hashes": [
                "sha256:stu901"
            ],
            "index": "pypi",
            "version": "==7.4.0"
        },
        "black": {
            "hashes": [
                "sha256:vwx234"
            ],
            "index": "pypi",
            "version": "==23.3.0"
        }
    }
}
"""