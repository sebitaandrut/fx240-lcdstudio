# SPDX-License-Identifier: GPL-3.0-or-later
"""Packaged-runtime smoke check with synthetic sensors and no device/config writes."""
import json
import os
from pathlib import Path
import sys


def run():
    # Select before QApplication construction; no display server is needed.
    os.environ['QT_QPA_PLATFORM']='offscreen'
    os.environ['QT_QUICK_BACKEND']='software'
    from PySide6.QtCore import QTimer,QObject
    from PySide6.QtWidgets import QApplication
    from PySide6.QtSvg import QSvgRenderer
    from .gui import create_engine,dispose_engine
    from .session import Settings,Session
    from .telemetry import Metric
    app=QApplication.instance() or QApplication(['fx240-self-test'])
    app.setQuitOnLastWindowClosed(False)
    attempts=[]
    def forbid(path):
        attempts.append(path)
        raise RuntimeError('Self-test must never open HID')
    def factory(settings,**kwargs):return Session(settings,transport_factory=forbid,**kwargs)
    metrics=[Metric('ct','CPU synthetic',45.125,'C','synthetic'),Metric('cf','CPU synthetic',4200,'MHz','synthetic'),
             Metric('gt','GPU synthetic',38,'C','synthetic'),Metric('gf','GPU synthetic',1800,'MHz','synthetic')]
    engine,bridge=create_engine(app,Settings(),provider=lambda:metrics,session_factory=factory)
    errors=[]
    root=Path(__file__).parent
    def inspect():
        try:
            window=engine.rootObjects()[0]
            assert window.title()=='FX240 LCD STUDIO'
            assert not window.grabWindow().isNull()
            assert bridge.session.frames>2
            assert bridge.sensorRows[0]['target']=='45.1°C'
            assert window.findChild(QObject,'brandIcon').property('implicitWidth')>0
            assert (root/'assets/fonts/Outfit.ttf').is_file()
            for name in ('dark','light','fallback'):
                assert QSvgRenderer(str(root/f'assets/branding/tray-lcd-{name}.svg')).isValid()
            for page in range(4):
                window.setProperty('page',page);app.processEvents()
                assert not window.grabWindow().isNull()
        except Exception as error:errors.append(str(error) or type(error).__name__)
        bridge.stop()
    def complete():
        if bridge.session is not None and not bridge.running:app.quit()
    bridge.changed.connect(complete)
    bridge.start({},False)
    QTimer.singleShot(750,inspect)
    QTimer.singleShot(5000,app.quit)
    app.exec()
    bridge.stop();bridge.session.thread.join(2)
    if bridge.running or bridge.session.thread.is_alive():errors.append('Worker did not stop')
    if attempts:errors.append('Unexpected HID access')
    result={'application':'FX240 LCD STUDIO','frozen':bool(getattr(sys,'frozen',False)),
            'qml_loaded':True,'frames':bridge.session.frames,'hid_open_attempts':len(attempts),
            'preferences_store_enabled':bridge.preferences is not None,'errors':errors}
    dispose_engine(engine)
    print(json.dumps(result),flush=True)
    return 1 if errors else 0
