# SPDX-License-Identifier: GPL-3.0-or-later
"""Temporary LCD drafts on the existing sender, separate from committed settings."""
from dataclasses import replace
from PySide6.QtCore import QObject,Property,Signal,Slot,QTimer


class LiveDraftPreview(QObject):
    changed=Signal()
    endRequested=Signal()

    def __init__(self,bridge):
        super().__init__(bridge)
        self.bridge=bridge
        self._ignore_until_stop=False
        self._active=False;self._finishing=False;self._original=None;self._target=None
        self._original_send=False;self._trial_send=True;self._paused=False
        self._finish_request=None;self._device=None;self._last_scene=None;self._close_after=False

    @Property(bool,notify=changed)
    def active(self):return self._active
    @Property(bool,notify=changed)
    def finishing(self):return self._finishing

    @Slot(result=bool)
    def start(self):
        bridge=self.bridge;workspace=bridge.workspace
        if self._ignore_until_stop or bridge._closing:return False
        if self._active:return True
        if not workspace.ready:
            workspace.reject('Wait for a valid preview before sending');return False
        device=bridge.settings.device or (bridge.devices[0] if len(bridge.devices)==1 else None)
        if not device:
            workspace.reject('Select an LCD device before visualizing the draft');return False
        if not bridge.running:bridge.start({},False)
        if not bridge.running:return False
        self._original=replace(bridge.settings,device=device);self._original_send=bridge.session.output_requested
        self._active=True;self._finishing=False;self._device=device
        self._trial_send=True;self._paused=False;self._last_scene=None;self._close_after=False
        if not self.validated(workspace.validatedScene):
            self.reset();return False
        self.changed.emit();return True

    def validated(self,scene):
        if not self._active or self._finishing:return False
        if scene==self._last_scene:return True
        try:
            config=replace(self.bridge.settings,layout_mode='editor',scene_json=scene,profile_id='',device=self._device)
            self.bridge.session.configure(config,self._trial_send)
            self._last_scene=scene
            return True
        except (OSError,ValueError) as error:
            self.bridge.workspace.reject(str(error));return False

    @Slot()
    def requestEnd(self):
        if self._active and not self._finishing:self.endRequested.emit()

    def request_close(self):
        self._close_after=True;self.requestEnd()

    @Slot()
    def continueEditing(self):self._close_after=False

    def pause_output(self):
        self._paused=True;self._trial_send=False
        # Replace a queued send=True edit or final decision before requesting standby.
        if self._finishing:
            self._finish_request=self.bridge.session.configure(self._target,False)
        else:
            config=replace(self.bridge.settings,layout_mode='editor',scene_json=self._last_scene,profile_id='',device=self._device)
            self.bridge.session.configure(config,False)
        self.bridge.session.set_output(False)
        self.requestEnd()

    @Slot(str,result=bool)
    def finish(self,action):
        if not self._active or self._finishing:return False
        if action not in ('apply','save','return'):return False
        bridge=self.bridge;workspace=bridge.workspace
        if action!='return' and not workspace.save(False,False):return False
        if self._close_after and action!='apply':
            # Exit goes directly to standby; a missing previous asset must not
            # trap the user in a trial or make an unsaved scene persistent.
            self.reset(closing=True)
            QTimer.singleShot(0,bridge.requestClose)
            return True
        if action=='apply':
            item=workspace.store.get(workspace.loadedId)
            target=replace(bridge.settings,layout_mode='editor',scene_json=item['scene'],profile_id=item['id'],device=self._device)
            send=not self._paused
        else:
            target=self._original;send=self._original_send and not self._paused
        try:request=bridge.session.configure(target,send)
        except (OSError,ValueError) as error:
            workspace.reject(str(error));return False
        self._target=target;self._finish_request=request;self._finishing=True;self.changed.emit()
        return True

    def frame(self,event):
        """Allow committing only the exact accepted final frame configuration."""
        if self._ignore_until_stop:return False
        if not self._active:return True
        if event.get('output_error'):self._trial_send=False
        if self._finishing:
            if event.get('config_request_id')!=self._finish_request:return False
            if event.get('config_error'):
                self._finishing=False;self._target=None
                self.bridge.workspace.reject('Could not finish LCD preview; retry or stop the display')
                self.changed.emit();self.endRequested.emit()
            elif event.get('configuration')==self._target:
                close=self._close_after
                self.reset()
                if close:QTimer.singleShot(0,self.bridge.requestClose)
                return True
        return False

    def reset(self,closing=False):
        self._ignore_until_stop=closing
        self._active=False;self._finishing=False;self._original=None;self._target=None
        self._device=None;self._last_scene=None;self._close_after=False
        self.changed.emit()
