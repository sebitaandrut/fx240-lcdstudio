# SPDX-License-Identifier: GPL-3.0-or-later
"""Inventory a trusted local PyInstaller build; no execution, network, or HID access.

This is a component/hash inventory, not a complete SBOM or vulnerability verdict.
Output excludes build/home paths, environment variables, and host identifiers.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from PyInstaller.archive.readers import CArchiveReader


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def version(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9][A-Za-z0-9.+_-]{0,63}', value) is None:
        raise ValueError('Invalid build version metadata')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in (args.binary.resolve(), args.manifest.resolve()):
        parser.error('Inventory output must not replace the executable or build manifest')
    manifest = json.loads(args.manifest.read_text())
    dependencies = manifest['dependencies']
    names = ('Pillow', 'PySide6-Essentials', 'shiboken6', 'PyInstaller',
             'pyinstaller-hooks-contrib', 'altgraph', 'packaging', 'setuptools')
    packages = {name: version(dependencies[name]) for name in names}
    archive = CArchiveReader(str(args.binary))
    components = []
    for name in sorted(archive.toc):
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Unexpected archive path; inventory was not written')
        if relative.name.endswith('.so') or '.so.' in relative.name:
            data = archive.extract(name)
            components.append({'file': relative.as_posix(),
                               'sha256': hashlib.sha256(data).hexdigest()})
    report = {
        'format': 'fx240-bundle-inventory-v1', 'complete_sbom': False,
        'artifact': 'fx240-lcd-studio', 'binary_sha256': sha256(args.binary),
        'python_version': version(manifest['python']),
        'qt_version': version(manifest['qt_version']),
        'python_distribution_versions': packages,
        'native_components': components,
        'limits': ['Trusted local build only; not a parser sandbox for hostile executables.',
                   'Shared-object filenames and hashes do not identify every dependency/version/license.',
                   'System libraries and unreported vulnerabilities are outside this inventory.']
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'inventory_written': True, 'native_components': len(components),
                      'complete_sbom': False}))


if __name__ == '__main__':
    main()
