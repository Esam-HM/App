#import distutils.spawn
import os
import re
import shlex
import subprocess
import sys


def get_install_requires():
    install_requires = [
        "gdown",
        "imgviz>=1.7.5",
        "matplotlib",
        "natsort>=7.1.0",
        "numpy",
        "onnxruntime>=1.14.1,!=1.16.0",
        "Pillow>=2.8",
        "PyYAML",
        "qtpy!=1.11.2",
        "scikit-image",
        "termcolor",
        "ultralytics"
    ]

    # Find python binding for qt with priority:
    # PyQt5 -> PySide2
    # and PyQt5 is automatically installed on Python3.
    QT_BINDING = None

    try:
        import PyQt5  # NOQA

        QT_BINDING = "pyqt5"
    except ImportError:
        pass

    if QT_BINDING is None:
        try:
            import PySide2  # NOQA

            QT_BINDING = "pyside2"
        except ImportError:
            pass

    if QT_BINDING is None:
        # PyQt5 can be installed via pip for Python3
        # 5.15.3, 5.15.4 won't work with PyInstaller
        install_requires.append("PyQt5!=5.15.3,!=5.15.4")
        QT_BINDING = "pyqt5"

    del QT_BINDING

    if os.name == "nt":  # Windows
        install_requires.append("colorama")

    return install_requires

def main():
    requirements = get_install_requires()
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + requirements)


if __name__ == "__main__":
    main()
