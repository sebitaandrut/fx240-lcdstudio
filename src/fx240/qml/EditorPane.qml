// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: editor
    required property var studio
    readonly property var workspace: bridge.workspace
    readonly property var state: workspace.model.selected
    readonly property bool hasSelection: workspace.model.selectedIndex>=0
    function tr(text) { return studio.tr(text) }
    component Copy: Label { color: studio.ink; textFormat: Text.PlainText; font.pixelSize: 14 }
    component Hint: Copy { color: studio.muted; wrapMode: Text.WordWrap }
    component Panel: Rectangle { color: studio.panel; radius: 16; border.color: studio.edge }
    component Tool: Button {
        property bool primary: false
        implicitHeight: 32; leftPadding: 10; rightPadding: 10
        contentItem: Copy { color: parent.primary ? "#08271e" : studio.ink; text: parent.text; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter; opacity: parent.enabled ? 1 : .4 }
        background: Rectangle { radius: 7; color: parent.primary ? studio.primaryFill : parent.hovered ? studio.selection : studio.controlColor; border.color: studio.edge }
    }
    component Choice: ComboBox {
        id: choice
        implicitHeight: 32
        contentItem: Copy { text: choice.displayText; verticalAlignment: Text.AlignVCenter; leftPadding: 8; rightPadding: 22; elide: Text.ElideRight }
        background: Rectangle { radius: 7; color: studio.controlColor; border.color: studio.edge }
        indicator: Copy { x: choice.width-22; y: (choice.height-height)/2; text: "⌄"; color: studio.muted }
        delegate: ItemDelegate {
            required property var modelData
            required property int index
            highlighted: choice.highlightedIndex===index
            width: choice.width-8; height: 34
            contentItem: Copy { text: parent.modelData; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: parent.highlighted ? studio.selection : parent.hovered ? studio.hoverColor : studio.panel }
        }
        popup: Popup {
            y: choice.height+4; width: choice.width; padding: 4; margins: 12
            implicitHeight: Math.min(contentItem.implicitHeight+8,230)
            background: Rectangle { color: studio.panel; border.color: studio.edge; radius: 8 }
            contentItem: ListView { implicitHeight: contentHeight; clip: true; model: choice.popup.visible ? choice.delegateModel : null; currentIndex: choice.highlightedIndex; ScrollBar.vertical: ScrollBar {} }
        }
    }
    component Entry: TextField {
        color: studio.ink; placeholderTextColor: studio.muted; implicitHeight: 34
        background: Rectangle { radius: 7; color: studio.controlColor; border.color: studio.edge }
    }
    component Toggle: Switch {
        id: toggle
        indicator: Rectangle {
            implicitWidth: 38; implicitHeight: 22; y: (toggle.height-height)/2; radius: 11
            color: toggle.checked ? studio.primaryFill : studio.controlColor; border.color: studio.edge
            Rectangle { x: toggle.checked ? parent.width-width-3 : 3; y: 3; width: 16; height: 16; radius: 8; color: toggle.checked ? "#08271e" : studio.muted }
        }
    }
    component Number: StudioNumber { studio: editor.studio; editable: true; implicitHeight: 32; from: 0; to: 239; Layout.fillWidth: true }
    AssetPicker {
        id: mediaDialog; objectName: "mediaAssetPicker"; studio: editor.studio; initialPath: editor.state.path || ""
        property bool replaceSelected: false
        title: editor.tr("Choose a background")
        onSelected: function(file) { workspace.addMedia(file,replaceSelected) }
    }
    Connections { target: workspace; function onDiscardRequested() { discardDialog.open() } }
    StudioConfirm {
        id: discardDialog; objectName: "discardDraftDialog"; studio: editor.studio
        title: editor.tr("Replace the unsaved draft?")
        message: editor.tr("Save it first, or discard the draft to continue.")
        acceptText: editor.tr("Discard draft")
        onAccepted: workspace.confirmDiscard()
        onRejected: workspace.cancelDiscard()
    }
    StudioConfirm {
        id: deleteDialog; objectName: "deleteProfileDialog"; studio: editor.studio
        title: editor.tr("Delete the saved profile?")
        message: editor.tr("The current draft stays available. Switch to Focus before deleting an active profile.")
        acceptText: editor.tr("Delete profile")
        onAccepted: workspace.deleteLoaded()
    }
    Connections { target: bridge.livePreview; function onEndRequested() { liveDialog.open() } function onChanged() { if (!bridge.livePreview.active && liveDialog.visible) liveDialog.close() } }
    StudioConfirm {
        id: liveDialog; objectName: "livePreviewDialog"; studio: editor.studio
        title: editor.tr("Finish LCD preview")
        message: editor.tr("Save and apply this design, or return to the previous output. Your draft stays available for editing.")
        onRejected: bridge.livePreview.continueEditing()
        contentItem: ColumnLayout {
            spacing: 12
            Hint { text: liveDialog.message; Layout.fillWidth: true }
            Entry { objectName: "liveProfileName"; text: workspace.profileName; placeholderText: editor.tr("Profile name"); maximumLength: 32; Layout.fillWidth: true; onTextEdited: workspace.setProfileName(text) }
            Hint { text: workspace.notice; visible: text.length>0; Layout.fillWidth: true }
        }
        footer: Item {
            implicitHeight: liveChoices.implicitHeight+36
            ColumnLayout {
                id: liveChoices; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 18; spacing: 8
                Tool { objectName: "liveSaveApply"; text: editor.tr("Save and apply"); primary: true; Layout.fillWidth: true; enabled: workspace.ready && workspace.profileName.trim().length>0; onClicked: { if (bridge.livePreview.finish("apply")) liveDialog.close() } }
                Tool { objectName: "liveSaveOnly"; text: editor.tr("Save and return to previous output"); Layout.fillWidth: true; enabled: workspace.ready && workspace.profileName.trim().length>0; onClicked: { if (bridge.livePreview.finish("save")) liveDialog.close() } }
                Tool { objectName: "liveReturn"; text: editor.tr("Return without saving"); Layout.fillWidth: true; onClicked: { if (bridge.livePreview.finish("return")) liveDialog.close() } }
                Tool { text: editor.tr("Keep editing live"); Layout.fillWidth: true; onClicked: { bridge.livePreview.continueEditing(); liveDialog.close() } }
            }
        }
    }
    ColumnLayout {
        anchors.fill: parent; spacing: 12
        ColumnLayout {
            objectName: "compositionToolbar"; Layout.fillWidth: true; spacing: 8
            RowLayout {
                objectName: "compositionPrimaryActions"; Layout.fillWidth: true; spacing: 8
                Tool { text: editor.tr("Back to designs"); onClicked: studio.page=0 }
                Entry { objectName: "profileNameControl"; Layout.minimumWidth: 180; Layout.fillWidth: true; text: workspace.profileName; placeholderText: editor.tr("Profile name"); maximumLength: 32; onTextEdited: workspace.setProfileName(text) }
                Tool { text: editor.tr("Save"); enabled: !bridge.livePreview.active && workspace.ready && workspace.profileName.trim().length>0; onClicked: workspace.save(false,false) }
                Tool { visible: !bridge.livePreview.active; primary: true; objectName: "saveAndShow"; text: editor.tr("Save and show"); enabled: workspace.ready && workspace.profileName.trim().length>0; onClicked: { if (workspace.save(true,false)) studio.page=0 } }
            }
            RowLayout {
                objectName: "compositionSecondaryActions"; Layout.fillWidth: true; spacing: 8
                Tool { enabled: !bridge.livePreview.active; text: editor.tr("New"); onClicked: workspace.requestNew() }
                Tool { text: editor.tr("Save copy"); enabled: !bridge.livePreview.active && workspace.ready && workspace.loadedId.length>0; onClicked: workspace.save(false,true) }
                Tool { objectName: "draftPreviewButton"; primary: true; text: editor.tr(bridge.livePreview.finishing ? "Finishing preview…" : bridge.livePreview.active ? "Finish LCD preview" : "Visualize on LCD"); enabled: !bridge.livePreview.finishing && (bridge.livePreview.active || workspace.ready); onClicked: { if (bridge.livePreview.active) bridge.livePreview.requestEnd(); else bridge.livePreview.start() } }
                Item { Layout.fillWidth: true }
                Tool { text: editor.tr("Delete profile"); enabled: !bridge.livePreview.active && workspace.loadedId.length>0; onClicked: { if (workspace.loadedId===bridge.activeProfileId) workspace.reject("Switch to Focus in Display before deleting this profile"); else deleteDialog.open() } }
            }
        }
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
        Panel {
            Layout.preferredWidth: 170; Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                Copy { text: editor.tr("Layers"); font.pixelSize: 19 }
                GridLayout { columns: 2; Layout.fillWidth: true; columnSpacing: 6; rowSpacing: 6
                    Tool { text: editor.tr("Reading"); Layout.fillWidth: true; onClicked: workspace.model.add("metric") }
                    Tool { text: editor.tr("Text"); Layout.fillWidth: true; onClicked: workspace.model.add("text") }
                    Tool { text: editor.tr("Image / GIF"); Layout.fillWidth: true; onClicked: { mediaDialog.replaceSelected=false; mediaDialog.open() } }
                    Tool { text: editor.tr("Arc"); Layout.fillWidth: true; onClicked: workspace.model.add("arc") }
                }
                ListView {
                    id: layerList; objectName: "editorLayers"
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                    model: workspace.model
                    delegate: Rectangle {
                        required property int index
                        required property string title
                        required property bool shown
                        width: layerList.width; height: 42; radius: 7
                        color: workspace.model.selectedIndex===index ? studio.selection : "transparent"
                        Copy { anchors.fill: parent; anchors.margins: 8; text: (parent.shown ? "● " : "○ ")+editor.tr(parent.title); elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                        MouseArea { anchors.fill: parent; onClicked: workspace.model.select(parent.index) }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
                Hint { text: editor.tr("Bottom layer first"); font.pixelSize: 12 }
                RowLayout { Layout.fillWidth: true; spacing: 6
                    Tool { text: "↓"; enabled: editor.hasSelection; Layout.fillWidth: true; onClicked: workspace.model.reorder(-1); Accessible.name: editor.tr("Send backward") }
                    Tool { text: "↑"; enabled: editor.hasSelection; Layout.fillWidth: true; onClicked: workspace.model.reorder(1); Accessible.name: editor.tr("Bring forward") }
                    Tool { text: "×"; enabled: editor.hasSelection; Layout.fillWidth: true; onClicked: workspace.model.removeSelected(); Accessible.name: editor.tr("Delete layer") }
                }
                Tool { text: editor.tr("Undo"); enabled: workspace.model.canUndo; Layout.fillWidth: true; onClicked: workspace.model.undo() }
            }
        }
        Panel {
            Layout.fillWidth: true; Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                RowLayout { Layout.fillWidth: true
                    Copy { text: editor.tr("Composition"); font.pixelSize: 19 }
                    Item { Layout.fillWidth: true }
                    Hint { text: "240 × 240" }
                }
                Item {
                    id: canvas; objectName: "editorCanvas"
                    Layout.preferredWidth: Math.max(180,Math.min(360,parent.width,parent.height-160)); Layout.preferredHeight: width
                    Layout.alignment: Qt.AlignHCenter
                    readonly property real zoom: width/240
                    Rectangle { anchors.fill: parent; color: "#080b0e"; radius: width/2; border.color: studio.edge }
                    Image { objectName: "editorFramePreview"; anchors.fill: parent; source: bridge.livePreview.active ? bridge.previewUrl : workspace.previewUrl; cache: false; smooth: true }
                    Repeater {
                        model: workspace.model
                        delegate: Rectangle {
                            id: layerBox; objectName: "editorLayer-"+layerId
                            required property int index
                            required property string layerId
                            required property real px
                            required property real py
                            required property real pw
                            required property real ph
                            required property bool shown
                            x: px*canvas.zoom; y: py*canvas.zoom
                            width: pw*canvas.zoom; height: ph*canvas.zoom
                            visible: shown
                            color: "transparent"; border.width: workspace.model.selectedIndex===index ? 1 : 0
                            border.color: studio.accent
                            MouseArea {
                                anchors.fill: parent; preventStealing: true; cursorShape: Qt.SizeAllCursor
                                property point origin
                                property point pressPoint
                                onPressed: function(mouse) {
                                    workspace.model.select(layerBox.index)
                                    workspace.model.beginGesture()
                                    origin=Qt.point(layerBox.px,layerBox.py)
                                    pressPoint=mapToItem(canvas,mouse.x,mouse.y)
                                }
                                onPositionChanged: function(mouse) {
                                    if (pressed) {
                                        var point=mapToItem(canvas,mouse.x,mouse.y)
                                        workspace.model.moveLayer(layerBox.layerId,origin.x+(point.x-pressPoint.x)/canvas.zoom,origin.y+(point.y-pressPoint.y)/canvas.zoom)
                                    }
                                }
                                onReleased: workspace.model.endGesture()
                                onCanceled: workspace.model.endGesture()
                            }
                            Rectangle {
                                visible: workspace.model.selectedIndex===layerBox.index
                                anchors.right: parent.right; anchors.bottom: parent.bottom
                                width: 12; height: 12; radius: 2; color: studio.accent
                                MouseArea {
                                    anchors.fill: parent; preventStealing: true; cursorShape: Qt.SizeFDiagCursor
                                    property point origin
                                    property point pressPoint
                                    onPressed: function(mouse) { origin=Qt.point(layerBox.pw,layerBox.ph); pressPoint=mapToItem(canvas,mouse.x,mouse.y); workspace.model.beginGesture() }
                                    onPositionChanged: function(mouse) {
                                        if (pressed) {
                                            var point=mapToItem(canvas,mouse.x,mouse.y)
                                            workspace.model.updateSelected({width:Math.max(12,Math.min(240-layerBox.px,Math.round(origin.x+(point.x-pressPoint.x)/canvas.zoom))),height:Math.max(12,Math.min(240-layerBox.py,Math.round(origin.y+(point.y-pressPoint.y)/canvas.zoom)))})
                                        }
                                    }
                                    onReleased: workspace.model.endGesture()
                                    onCanceled: workspace.model.endGesture()
                                }
                            }
                        }
                    }
                    Rectangle { anchors.fill: parent; radius: width/2; color: "transparent"; border.color: studio.edge }
                }
                Hint { text: editor.tr("Drag to move. Use the corner handle to resize. Content outside the circle is clipped."); Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                Item { Layout.fillHeight: true }
                Hint { text: editor.tr(bridge.livePreview.active ? "Live LCD preview · unsaved profile changes." : "Draft preview · save and select it in Display to use it on the LCD."); Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            }
        }
        Panel {
            Layout.minimumWidth: 230; Layout.preferredWidth: Math.max(250,Math.min(330,studio.width*.25)); Layout.fillHeight: true
            ScrollView {
                id: propertiesScroll
                anchors.fill: parent; anchors.margins: 16; rightPadding: 12; clip: true; contentWidth: availableWidth
                ColumnLayout {
                    width: propertiesScroll.availableWidth; spacing: 12
                    Copy { text: editor.tr("Properties"); font.pixelSize: 19 }
                    Hint { visible: !editor.hasSelection; text: editor.tr("Select a layer to edit it."); Layout.fillWidth: true }
                    ColumnLayout {
                        visible: editor.hasSelection; Layout.fillWidth: true; spacing: 10
                        RowLayout { Layout.fillWidth: true
                            Copy { text: editor.tr("Visible") }
                            Item { Layout.fillWidth: true }
                            Toggle { checked: editor.state.visible===true; onToggled: workspace.model.updateSelected({visible:checked}) }
                        }
                        GridLayout { columns: 2; Layout.fillWidth: true
                            Hint { text: "X" } Number { to: 240-(editor.state.width || 12); value: editor.state.x || 0; objectName: "editorX"; onValueModified: workspace.model.updateSelected({x:value}) }
                            Hint { text: "Y" } Number { to: 240-(editor.state.height || 12); value: editor.state.y || 0; onValueModified: workspace.model.updateSelected({y:value}) }
                            Hint { text: editor.tr("Width") } Number { from: 12; to: 240-(editor.state.x || 0); value: editor.state.width || 12; onValueModified: workspace.model.updateSelected({width:value}) }
                            Hint { text: editor.tr("Height") } Number { from: 12; to: 240-(editor.state.y || 0); value: editor.state.height || 12; onValueModified: workspace.model.updateSelected({height:value}) }
                        }
                        ColumnLayout { visible: editor.state.kind==="metric"; Layout.fillWidth: true
                            Hint { text: editor.tr("Reading") }
                            Choice { Layout.fillWidth: true; model: [editor.tr("CPU temperature"),editor.tr("CPU frequency"),editor.tr("GPU temperature"),editor.tr("GPU frequency")]; currentIndex: ["cpu_temp","cpu_clock","gpu_temp","gpu_clock"].indexOf(editor.state.metric); onActivated: function(index) { workspace.model.updateSelected({metric:["cpu_temp","cpu_clock","gpu_temp","gpu_clock"][index]}) } }
                            Entry { text: editor.state.label || ""; placeholderText: editor.tr("Optional label"); maximumLength: 32; Layout.fillWidth: true; objectName: "layerLabelControl"; onTextEdited: workspace.model.updateSelected({label:text}) }
                        }
                        Entry { visible: editor.state.kind==="text"; text: editor.state.text || ""; maximumLength: 160; Layout.fillWidth: true; onTextEdited: workspace.model.updateSelected({text:text}) }
                        ColumnLayout { visible: editor.state.kind==="metric" || editor.state.kind==="text"; Layout.fillWidth: true
                            Hint { text: editor.tr("Typeface") }
                            RowLayout { Layout.fillWidth: true
                                FontPicker { studio: editor.studio; model: [editor.tr("Global typeface")].concat(bridge.systemFontLabels.slice(1)); Layout.fillWidth: true; displayText: editor.state.font_path ? bridge.fontLabel(editor.state.font_path) : editor.tr("Global typeface"); onActivated: function(index) { workspace.model.updateSelected({font_path:bridge.systemFontPath(index) || null}) } }
                                Tool { text: "↻"; enabled: !bridge.fontDiscoveryBusy; onClicked: bridge.refreshSystemFonts(); Accessible.name: editor.tr("Refresh") }
                            }
                            GridLayout { columns: 2; Layout.fillWidth: true
                                Hint { text: editor.tr("Size") } Number { from: 6; to: 72; value: editor.state.size || 24; onValueModified: workspace.model.updateSelected({size:value}) }
                                Hint { text: editor.tr("Weight"); visible: workspace.fontInfo.variable===true }
                                Number { visible: workspace.fontInfo.variable===true; from: workspace.fontInfo.minimum || 100; to: workspace.fontInfo.maximum || 900; stepSize: 50; value: editor.state.weight || 350; onValueModified: workspace.model.updateSelected({weight:value}) }
                            }
                            Hint { visible: workspace.fontInfo.variable!==true; text: editor.tr("Static font: select an installed style to change its weight."); Layout.fillWidth: true }
                            Choice { objectName: "staticStyleControl"; visible: workspace.fontInfo.variable!==true; Layout.fillWidth: true; model: workspace.fontStyles; currentIndex: workspace.fontStyleIndex; onActivated: function(index) { workspace.selectFontStyle(index) } }
                            Choice { Layout.fillWidth: true; model: [editor.tr("Left"),editor.tr("Center"),editor.tr("Right")]; currentIndex: ["left","center","right"].indexOf(editor.state.align); onActivated: function(index) { workspace.model.updateSelected({align:["left","center","right"][index]}) } }
                        }
                        Choice { visible: editor.state.kind==="arc"; Layout.fillWidth: true; model: [editor.tr("Comet"),editor.tr("Orbit"),editor.tr("Pulse"),editor.tr("Static")]; currentIndex: ["comet","orbit","pulse","none"].indexOf(editor.state.animation); onActivated: function(index) { workspace.model.updateSelected({animation:["comet","orbit","pulse","none"][index]}) } }
                        Hint { visible: editor.state.kind!=="media"; text: editor.tr("Color") }
                        RowLayout { visible: editor.state.kind!=="media"; spacing: 7
                            Repeater { model: ["#edf4f5","#73dfc1","#68b5ff","#ac8aff","#ff83b5","#ffb86b"]
                                delegate: Rectangle { required property string modelData; width: 24; height: 24; radius: 12; color: modelData; border.color: studio.ink; border.width: editor.state.color===modelData ? 2 : 0; MouseArea { anchors.fill: parent; onClicked: workspace.model.updateSelected({color:parent.modelData}) } }
                            }
                        }
                        Entry { visible: editor.state.kind!=="media"; text: editor.state.color || "#edf4f5"; maximumLength: 7; Layout.fillWidth: true; placeholderText: "#RRGGBB"; validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
                            onTextEdited: { if (acceptableInput) workspace.model.updateSelected({color:text}) } }
                        Tool { visible: editor.state.kind==="media"; text: editor.tr("Replace image / GIF…"); Layout.fillWidth: true; onClicked: { mediaDialog.replaceSelected=true; mediaDialog.open() } }
                        Hint { text: editor.tr("Opacity")+" · "+Math.round((editor.state.opacity===undefined ? 1 : editor.state.opacity)*100)+"%" }
                        Slider { from: 0; to: 1; stepSize: .05; value: editor.state.opacity===undefined ? 1 : editor.state.opacity; Layout.fillWidth: true; onMoved: workspace.model.updateSelected({opacity:value}) }
                        Tool { text: editor.tr("Delete layer"); Layout.fillWidth: true; onClicked: workspace.model.removeSelected() }
                    }
                    Hint { text: workspace.notice; visible: text.length>0; color: studio.errorColor; Layout.fillWidth: true }
                    Hint { text: bridge.fontNotice; visible: text.length>0; Layout.fillWidth: true }
                }
            }
        }
    }
    }
}
