// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls

Slider {
    id: control
    required property var studio
    implicitHeight: 24
    padding: 0

    background: Rectangle {
        x: control.leftPadding + control.handle.width / 2
        y: control.topPadding + (control.availableHeight - height) / 2
        width: Math.max(0, control.availableWidth - control.handle.width)
        height: 4
        radius: 2
        color: control.studio.edge
        opacity: control.enabled ? 1 : 0.45

        Rectangle {
            x: control.mirrored ? parent.width - width : 0
            width: parent.width * control.position
            height: parent.height
            radius: parent.radius
            color: control.studio.accent
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * Math.max(0, control.availableWidth - width)
        y: control.topPadding + (control.availableHeight - height) / 2
        width: 14
        height: 14
        radius: 7
        color: control.studio.ink
        opacity: control.enabled ? 1 : 0.45
        border.width: control.visualFocus ? 2 : 0
        border.color: control.studio.accent
    }
}
