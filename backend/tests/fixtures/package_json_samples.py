"""
Test fixtures for package.json files
"""

# Basic package.json with production and dev dependencies
BASIC_PACKAGE_JSON = {
    "name": "test-app",
    "version": "1.0.0",
    "description": "Test application",
    "dependencies": {
        "express": "^4.18.2",
        "lodash": "4.17.21",
        "axios": "~1.6.0"
    },
    "devDependencies": {
        "jest": "^29.0.0",
        "typescript": "5.0.4"
    }
}

# Complex package.json with various dependency types
COMPLEX_PACKAGE_JSON = {
    "name": "complex-app",
    "version": "2.1.0",
    "dependencies": {
        "react": "^18.2.0",
        "lodash": "4.17.21",
        "moment": ">=2.29.0",
        "chalk": "~4.1.0",
        "git-package": "git+https://github.com/user/repo.git#v1.0.0",
        "local-package": "file:../local-dep",
        "scoped-package": "@babel/core"
    },
    "devDependencies": {
        "@types/node": "^18.0.0",
        "eslint": "8.45.0",
        "prettier": "*"
    },
    "peerDependencies": {
        "react": ">=16.0.0"
    },
    "optionalDependencies": {
        "fsevents": "^2.3.2"
    }
}

# Minimal package.json with no dependencies
MINIMAL_PACKAGE_JSON = {
    "name": "minimal-app",
    "version": "1.0.0",
    "main": "index.js"
}

# Malformed package.json (missing required fields)
MALFORMED_PACKAGE_JSON = {
    "dependencies": {
        "express": "^4.18.2"
    }
    # Missing name and version
}