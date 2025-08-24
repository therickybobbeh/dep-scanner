"""
Test fixtures for package-lock.json files (both v1 and v2+ formats)
"""

# Package-lock.json v1 format (nested dependencies)
PACKAGE_LOCK_V1 = {
    "name": "test-app",
    "version": "1.0.0",
    "lockfileVersion": 1,
    "requires": True,
    "dependencies": {
        "express": {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
            "integrity": "sha512-5/PsL6iGPdfQ/lKM1UuielYgv3BUoJfz1aUwU9vHZ+J7gyvwdQXFEBIEIaxeGf0GIcreATNyBExtalisDbuMqQ==",
            "requires": {
                "accepts": "~1.3.8",
                "array-flatten": "1.1.1",
                "cookie": "0.5.0"
            },
            "dependencies": {
                "accepts": {
                    "version": "1.3.8",
                    "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.8.tgz",
                    "integrity": "sha512-PYAthTa2m2VKxuvSD3DPC/Gy+U+sOA1LAuT8mkmRuvw+NACSaeXEQ+NHcVF7rONl6qcaxV3Uuemwawk+7+SJLw==",
                    "requires": {
                        "mime-types": "~2.1.34",
                        "negotiator": "0.6.3"
                    }
                },
                "mime-types": {
                    "version": "2.1.35",
                    "resolved": "https://registry.npmjs.org/mime-types/-/mime-types-2.1.35.tgz",
                    "integrity": "sha512-ZDY+bPm5zTTF+YpCrAU9nK0UgICYPT0QtT1NZWFv4s++TNkcgVaT0g6+4R2uI4MjQjzysHB1zxuWL50hzaeXiw==",
                    "requires": {
                        "mime-db": "1.52.0"
                    }
                },
                "mime-db": {
                    "version": "1.52.0",
                    "resolved": "https://registry.npmjs.org/mime-db/-/mime-db-1.52.0.tgz",
                    "integrity": "sha512-sPU4uV7dYlvtWJxwwxHD0PuihVNiE7TyAbQ5SWxDCB9mUYvOgroQOwYQQOKPJ8CIbE+1ETVlOoK1UC2nU3gYvg=="
                },
                "negotiator": {
                    "version": "0.6.3",
                    "resolved": "https://registry.npmjs.org/negotiator/-/negotiator-0.6.3.tgz",
                    "integrity": "sha512-+EUsqGPLsM+j/zdChZjsnX51g4XrHFOIXwfnCVPGlQk/k5giakcKsuxCObBRu6DSm9opw/O6slWbJdghQM4bBg=="
                }
            }
        },
        "array-flatten": {
            "version": "1.1.1",
            "resolved": "https://registry.npmjs.org/array-flatten/-/array-flatten-1.1.1.tgz",
            "integrity": "sha1-ml9pkFGx5wczKPKgCJaLZOopVdI="
        },
        "cookie": {
            "version": "0.5.0",
            "resolved": "https://registry.npmjs.org/cookie/-/cookie-0.5.0.tgz",
            "integrity": "sha512-YZ3GUyn/o8gfKJlnlX7g7xq4gyO6OSuhGPKaaGssGB2qgDUS0gPgtTvoyZLTt9Ab6dC4hfc9dV5arkvc/OCmrw=="
        },
        "lodash": {
            "version": "4.17.21",
            "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
            "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZVGedAJv8XZ1tvj5FvSg=="
        },
        "jest": {
            "version": "29.7.0",
            "resolved": "https://registry.npmjs.org/jest/-/jest-29.7.0.tgz",
            "integrity": "sha512-NIy3oAFp9shda19hy4HK0HRTWKtPJmGdnvywu01nOqNC2vZg+Z+fvJDxpMQA88eb2I9EcafcdjYgsDthnYTvGw==",
            "dev": True
        }
    }
}

# Package-lock.json v2+ format (flat packages structure)
PACKAGE_LOCK_V2 = {
    "name": "test-app",
    "version": "1.0.0",
    "lockfileVersion": 2,
    "requires": True,
    "packages": {
        "": {
            "name": "test-app",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.2",
                "lodash": "4.17.21"
            },
            "devDependencies": {
                "jest": "^29.7.0"
            }
        },
        "node_modules/express": {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
            "integrity": "sha512-5/PsL6iGPdfQ/lKM1UuielYgv3BUoJfz1aUwU9vHZ+J7gyvwdQXFEBIEIaxeGf0GIcreATNyBExtalisDbuMqQ==",
            "dependencies": {
                "accepts": "~1.3.8",
                "array-flatten": "1.1.1",
                "cookie": "0.5.0"
            }
        },
        "node_modules/accepts": {
            "version": "1.3.8",
            "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.8.tgz",
            "integrity": "sha512-PYAthTa2m2VKxuvSD3DPC/Gy+U+sOA1LAuT8mkmRuvw+NACSaeXEQ+NHcVF7rONl6qcaxV3Uuemwawk+7+SJLw==",
            "dependencies": {
                "mime-types": "~2.1.34",
                "negotiator": "0.6.3"
            }
        },
        "node_modules/mime-types": {
            "version": "2.1.35",
            "resolved": "https://registry.npmjs.org/mime-types/-/mime-types-2.1.35.tgz",
            "integrity": "sha512-ZDY+bPm5zTTF+YpCrAU9nK0UgICYPT0QtT1NZWFv4s++TNkcgVaT0g6+4R2uI4MjQjzysHB1zxuWL50hzaeXiw==",
            "dependencies": {
                "mime-db": "1.52.0"
            }
        },
        "node_modules/mime-db": {
            "version": "1.52.0",
            "resolved": "https://registry.npmjs.org/mime-db/-/mime-db-1.52.0.tgz",
            "integrity": "sha512-sPU4uV7dYlvtWJxwwxHD0PuihVNiE7TyAbQ5SWxDCB9mUYvOgroQOwYQQOKPJ8CIbE+1ETVlOoK1UC2nU3gYvg=="
        },
        "node_modules/negotiator": {
            "version": "0.6.3",
            "resolved": "https://registry.npmjs.org/negotiator/-/negotiator-0.6.3.tgz",
            "integrity": "sha512-+EUsqGPLsM+j/zdChZjsnX51g4XrHFOIXwfnCVPGlQk/k5giakcKsuxCObBRu6DSm9opw/O6slWbJdghQM4bBg=="
        },
        "node_modules/array-flatten": {
            "version": "1.1.1",
            "resolved": "https://registry.npmjs.org/array-flatten/-/array-flatten-1.1.1.tgz",
            "integrity": "sha1-ml9pkFGx5wczKPKgCJaLZOopVdI="
        },
        "node_modules/cookie": {
            "version": "0.5.0",
            "resolved": "https://registry.npmjs.org/cookie/-/cookie-0.5.0.tgz",
            "integrity": "sha512-YZ3GUyn/o8gfKJlnlX7g7xq4gyO6OSuhGPKaaGssGB2qgDUS0gPgtTvoyZLTt9Ab6dC4hfc9dV5arkvc/OCmrw=="
        },
        "node_modules/lodash": {
            "version": "4.17.21",
            "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
            "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZVGedAJv8XZ1tvj5FvSg=="
        },
        "node_modules/jest": {
            "version": "29.7.0",
            "resolved": "https://registry.npmjs.org/jest/-/jest-29.7.0.tgz",
            "integrity": "sha512-NIy3oAFp9shda19hy4HK0HRTWKtPJmGdnvywu01nOqNC2vZg+Z+fvJDxpMQA88eb2I9EcafcdjYgsDthnYTvGw==",
            "dev": True
        }
    }
}

# Package-lock.json v3 format (similar to v2 but with updated structure)
PACKAGE_LOCK_V3 = {
    "name": "test-app",
    "version": "1.0.0",
    "lockfileVersion": 3,
    "requires": True,
    "packages": {
        "": {
            "name": "test-app",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.2"
            }
        },
        "node_modules/express": {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
            "integrity": "sha512-5/PsL6iGPdfQ/lKM1UuielYgv3BUoJfz1aUwU9vHZ+J7gyvwdQXFEBIEIaxeGf0GIcreATNyBExtalisDbuMqQ=="
        }
    }
}

# Malformed package-lock.json
MALFORMED_PACKAGE_LOCK = {
    "name": "test-app",
    "lockfileVersion": 2,
    # Missing packages or dependencies section
}