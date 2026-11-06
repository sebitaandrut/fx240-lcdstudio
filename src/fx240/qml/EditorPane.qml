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
    readonly property bool multiple: workspace.model.selectionCount > 1
    readonly property bool editingGradient: !multiple && state.kind === "gradient"
    readonly property bool editingMotion: !multiple && (state.kind === "arc" ||
        (state.kind === "effect" && !["disc", "divider"].includes(state.effect)))
    readonly property var bounds: workspace.model.selectionBounds
    function tr(text) { return studio.tr(text) }
    function chooseGradientColor(button, label, field) {
        const layerId = state.id
        studio.chooseEditorColor(button, tr(label), state[field], function(color) {
            if (editor.editingGradient && editor.state.id === layerId)
                workspace.model.updateSelected({[field]: color})
        })
    }
    function chooseLayerColor(button) {
        const layerId = state.id
        const count = workspace.model.selectionCount
        studio.chooseEditorColor(button, tr("Color"), state.color, function(color) {
            if (editor.state.id === layerId && workspace.model.selectionCount === count)
                workspace.model.updateSelectionStyle({color: color})
        })
    }
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
    Popup {
        id: effectsMenu
        objectName: "effectsMenu"
        width: 260; padding: 8; margins: 12
        x: effectsButton.width + 6
        y: 0
        parent: effectsButton
        focus: true
        background: Panel {}
        contentItem: ColumnLayout {
            spacing: 4
            Repeater {
                model: effectsMenu.visible ? workspace.model.effectCatalog : []
                delegate: Tool {
                    id: effectEntry
                    required property var modelData
                    objectName: "addEffect-" + modelData.key
                    text: editor.tr(modelData.label)
                    Layout.fillWidth: true
                    implicitHeight: 44
                    contentItem: RowLayout {
                        spacing: 10
                        Image {
                            Layout.preferredWidth: 32; Layout.preferredHeight: 32
                            source: "image://effects/" + effectEntry.modelData.key
                            smooth: true; Accessible.ignored: true
                        }
                        Copy { text: effectEntry.text; Layout.fillWidth: true }
                    }
                    onClicked: {
                        workspace.model.addEffect(modelData.key)
                        effectsMenu.close()
                    }
                }
            }
        }
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
    AssetPicker {
        id: fontDialog; objectName: "fontAssetPicker"; studio: editor.studio; kind: "font"
        initialPath: editor.state.font_path || ""
        property string layerId
        title: editor.tr("Choose a font")
        onSelected: function(file) {
            const path = bridge.localPath(file)
            if (path && editor.state.id === layerId) workspace.model.updateSelected({font_path: path})
        }
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
        message: editor.tr("The current draft stays available. Activate another design before deleting the one in use.")
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
    StudioConfirm {
        id: clearDialog; objectName: "clearCompositionDialog"; studio: editor.studio
        title: editor.tr("Remove all layers?")
        message: editor.tr("This clears the draft, not the saved profile. Undo restores the layers. During LCD preview, the cleared draft is shown live.")
        acceptText: editor.tr("Clear all")
        onAccepted: workspace.model.resetComposition(true)
    }
    ColumnLayout {
        anchors.fill: parent; spacing: 12
        ColumnLayout {
            objectName: "compositionToolbar"; Layout.fillWidth: true; spacing: 8
            RowLayout {
                objectName: "compositionPrimaryActions"; Layout.fillWidth: true; spacing: 8
                Tool { text: editor.tr("Back to designs"); onClicked: studio.page=0 }
                Entry { objectName: "profileNameControl"; Layout.minimumWidth: 180; Layout.preferredWidth: 380; Layout.maximumWidth: 460; text: workspace.profileName; placeholderText: editor.tr("Profile name"); maximumLength: 32; onTextEdited: workspace.setProfileName(text) }
                Tool { text: editor.tr("Save"); enabled: !bridge.livePreview.active && workspace.ready && workspace.profileName.trim().length>0; onClicked: workspace.save(false,false) }
                Tool { visible: !bridge.livePreview.active; primary: true; objectName: "saveAndShow"; text: editor.tr("Save and show"); enabled: workspace.ready && workspace.profileName.trim().length>0; onClicked: { if (workspace.save(true,false)) studio.page=0 } }
                Item { Layout.fillWidth: true }
            }
            RowLayout {
                objectName: "compositionSecondaryActions"; Layout.fillWidth: true; spacing: 8
                Tool { enabled: !bridge.livePreview.active; text: editor.tr("New"); onClicked: workspace.requestNew() }
                Tool { text: editor.tr("Save copy"); enabled: !bridge.livePreview.active && workspace.ready && workspace.loadedId.length>0; onClicked: workspace.save(false,true) }
                Tool { objectName: "draftPreviewButton"; primary: true; text: editor.tr(bridge.livePreview.finishing ? "Finishing preview…" : bridge.livePreview.active ? "Finish LCD preview" : "Visualize on LCD"); enabled: !bridge.livePreview.finishing && (bridge.livePreview.active || workspace.ready); onClicked: { if (bridge.livePreview.active) bridge.livePreview.requestEnd(); else bridge.livePreview.start() } }
                Tool { text: editor.tr("Delete profile"); enabled: !bridge.livePreview.active && workspace.loadedId.length>0; onClicked: { if (workspace.loadedId===bridge.activeProfileId) workspace.reject("Activate another design before deleting the one in use"); else deleteDialog.open() } }
                Item { Layout.fillWidth: true }
            }
        }
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
        Panel {
            objectName: "editorLayersPanel"
            Layout.preferredWidth: Math.max(170, Math.min(320, editor.width * .15))
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                Copy { text: editor.tr("Layers"); font.pixelSize: 19 }
                GridLayout { columns: 2; Layout.fillWidth: true; columnSpacing: 6; rowSpacing: 6
                    Tool { text: editor.tr("Reading"); Layout.fillWidth: true; onClicked: workspace.model.add("metric") }
                    Tool { text: editor.tr("Text"); Layout.fillWidth: true; onClicked: workspace.model.add("text") }
                    Tool { text: editor.tr("Image / GIF"); Layout.columnSpan: 2; Layout.fillWidth: true; onClicked: { mediaDialog.replaceSelected=false; mediaDialog.open() } }
                    Tool { objectName: "addGradientLayer"; text: editor.tr("Gradient"); Layout.columnSpan: 2; Layout.fillWidth: true; onClicked: workspace.model.add("gradient") }
                    Tool {
                        id: effectsButton; objectName: "addEffectsButton"
                        text: "+ " + editor.tr("Effects")
                        Layout.columnSpan: 2; Layout.fillWidth: true
                        onClicked: effectsMenu.open()
                    }
                }
                ListView {
                    id: layerList; objectName: "editorLayers"
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                    model: workspace.model
                    delegate: Rectangle {
                        required property int index
                        required property string title
                        id: layerRow
                        required property bool shown
                        required property bool marked
                        objectName: "editorLayerRow-"+index
                        width: layerList.width; height: 42; radius: 7
                        color: marked ? studio.selection : "transparent"
                        MouseArea {
                            anchors.fill: parent
                            onClicked: function(mouse) {
                                if (mouse.modifiers & Qt.ShiftModifier) workspace.model.toggleSelection(layerRow.index)
                                else workspace.model.select(layerRow.index)
                            }
                        }
                        CheckBox {
                            id: layerCheck
                            objectName: "editorLayerCheck-"+layerRow.index
                            width: 34; height: parent.height; checked: layerRow.marked
                            Accessible.name: editor.tr("Select layer")+" · "+editor.tr(layerRow.title)
                            indicator: Rectangle {
                                x: (layerCheck.width-width)/2; y: (layerCheck.height-height)/2
                                width: 16; height: 16; radius: 4
                                color: layerCheck.checked ? studio.primaryFill : studio.controlColor
                                border.color: layerCheck.activeFocus ? studio.accent : studio.muted
                                Copy { anchors.centerIn: parent; text: "✓"; color: "#08271e"; visible: layerCheck.checked }
                            }
                            onClicked: workspace.model.toggleSelection(layerRow.index)
                        }
                        Copy {
                            anchors.left: layerCheck.right; anchors.right: parent.right; anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: editor.tr(layerRow.title); elide: Text.ElideRight
                            opacity: layerRow.shown ? 1 : .55
                        }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
                Hint { text: editor.tr("Bottom layer first"); font.pixelSize: 12 }
                RowLayout { Layout.fillWidth: true; spacing: 6
                    Tool { text: "↓"; enabled: editor.hasSelection && !editor.multiple; Layout.fillWidth: true; onClicked: workspace.model.reorder(-1); Accessible.name: editor.tr("Send backward") }
                    Tool { text: "↑"; enabled: editor.hasSelection && !editor.multiple; Layout.fillWidth: true; onClicked: workspace.model.reorder(1); Accessible.name: editor.tr("Bring forward") }
                    Tool { objectName: "deleteSelectedLayers"; text: "×"; enabled: editor.hasSelection; Layout.fillWidth: true; onClicked: workspace.model.removeSelected(); Accessible.name: editor.tr(editor.multiple ? "Delete selected layers" : "Delete layer") }
                }
                Tool { objectName: "clearCompositionButton"; text: editor.tr("Clear all"); enabled: layerList.count>0 && !bridge.livePreview.finishing; Layout.fillWidth: true; onClicked: clearDialog.open() }
                Tool { objectName: "editorUndoButton"; text: editor.tr("Undo"); enabled: workspace.model.canUndo; Layout.fillWidth: true; onClicked: workspace.model.undo() }
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
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.minimumHeight: 180
                    Item {
                        id: canvas; objectName: "editorCanvas"; clip: true
                        anchors.centerIn: parent
                        width: Math.min(660, parent.width, parent.height); height: width
                        readonly property real zoom: width/240
                        Rectangle { anchors.fill: parent; color: "#080b0e"; radius: width/2; border.color: studio.edge }
                        Image {
                            objectName: "editorFramePreview"; anchors.fill: parent
                            source: bridge.livePreview.showOutput ? bridge.previewUrl : workspace.previewUrl
                            retainWhileLoading: true; cache: false; smooth: true
                        }
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
                                required property bool marked
                                required property real angle
                                rotation: angle; transformOrigin: Item.Center
                                x: px*canvas.zoom; y: py*canvas.zoom
                                width: pw*canvas.zoom; height: ph*canvas.zoom
                                visible: shown
                                color: "transparent"; border.width: marked ? 1 : 0
                                border.color: studio.accent
                                MouseArea {
                                    anchors.fill: parent; preventStealing: true; cursorShape: Qt.SizeAllCursor
                                    property bool dragging: false
                                    property bool shiftPressed: false
                                    property point pressPoint
                                    function startDrag() {
                                        if (shiftPressed && !layerBox.marked) workspace.model.toggleSelection(layerBox.index)
                                        workspace.model.selectForDrag(layerBox.index)
                                        workspace.model.beginGesture()
                                        dragging=true
                                    }
                                    onPressed: function(mouse) {
                                        pressPoint=mapToItem(canvas,mouse.x,mouse.y)
                                        shiftPressed=Boolean(mouse.modifiers & Qt.ShiftModifier)
                                        if (!shiftPressed) startDrag()
                                    }
                                    onPositionChanged: function(mouse) {
                                        if (!pressed) return
                                        const point=mapToItem(canvas,mouse.x,mouse.y)
                                        const dx=point.x-pressPoint.x, dy=point.y-pressPoint.y
                                        if (!dragging && Math.abs(dx)+Math.abs(dy)>=4) startDrag()
                                        if (dragging) workspace.model.moveSelection(dx/canvas.zoom,dy/canvas.zoom)
                                    }
                                    onReleased: {
                                        if (dragging) workspace.model.endGesture()
                                        else if (shiftPressed) workspace.model.toggleSelection(layerBox.index)
                                        dragging=false
                                    }
                                    onCanceled: {
                                        if (dragging) workspace.model.endGesture()
                                        dragging=false
                                    }
                                }
                                Rectangle {
                                    objectName: "editorResize-"+layerId
                                    visible: layerBox.marked && !editor.multiple
                                    anchors.right: parent.right; anchors.bottom: parent.bottom
                                    width: 12; height: 12; radius: 2; color: studio.accent
                                    MouseArea {
                                        anchors.fill: parent; preventStealing: true; cursorShape: Qt.SizeFDiagCursor
                                        property rect originBounds
                                        property point pressPoint
                                        onPressed: function(mouse) { originBounds=Qt.rect(layerBox.px,layerBox.py,layerBox.pw,layerBox.ph); pressPoint=mapToItem(canvas,mouse.x,mouse.y); workspace.model.beginGesture() }
                                        onPositionChanged: function(mouse) {
                                            if (pressed) {
                                                var point=mapToItem(canvas,mouse.x,mouse.y)
                                                var dx=(point.x-pressPoint.x)/canvas.zoom, dy=(point.y-pressPoint.y)/canvas.zoom
                                                var radians=layerBox.angle*Math.PI/180, c=Math.cos(radians), s=Math.sin(radians)
                                                var w=Math.max(12,Math.min(240,Math.round(originBounds.width+c*dx+s*dy)))
                                                var h=Math.max(12,Math.min(240,Math.round(originBounds.height-s*dx+c*dy)))
                                                var dw=w-originBounds.width, dh=h-originBounds.height
                                                var x=Math.max(0,Math.min(240-w,Math.round(originBounds.x+((c-1)*dw-s*dh)/2)))
                                                var y=Math.max(0,Math.min(240-h,Math.round(originBounds.y+(s*dw+(c-1)*dh)/2)))
                                                workspace.model.updateSelected({x:x,y:y,width:w,height:h})
                                            }
                                        }
                                        onReleased: workspace.model.endGesture()
                                        onCanceled: workspace.model.endGesture()
                                    }
                                }
                            }
                        }
                        Rectangle {
                            visible: editor.multiple; z: 1
                            x: (editor.bounds.x || 0)*canvas.zoom; y: (editor.bounds.y || 0)*canvas.zoom
                            width: (editor.bounds.width || 0)*canvas.zoom; height: (editor.bounds.height || 0)*canvas.zoom
                            color: "transparent"; border.color: studio.accent
                            Rectangle {
                                objectName: "editorGroupResize"
                                anchors.right: parent.right; anchors.bottom: parent.bottom
                                width: 12; height: 12; radius: 2; color: studio.accent
                                MouseArea {
                                    anchors.fill: parent; preventStealing: true; cursorShape: Qt.SizeFDiagCursor
                                    property point pressPoint
                                    property point diagonal
                                    onPressed: function(mouse) {
                                        pressPoint=mapToItem(canvas,mouse.x,mouse.y)
                                        diagonal=Qt.point(editor.bounds.width*canvas.zoom,editor.bounds.height*canvas.zoom)
                                        workspace.model.beginGesture()
                                    }
                                    onPositionChanged: function(mouse) {
                                        if (!pressed) return
                                        const point=mapToItem(canvas,mouse.x,mouse.y)
                                        const dx=point.x-pressPoint.x, dy=point.y-pressPoint.y
                                        workspace.model.scaleSelection(1+(dx*diagonal.x+dy*diagonal.y)/(diagonal.x*diagonal.x+diagonal.y*diagonal.y))
                                    }
                                    onReleased: workspace.model.endGesture()
                                    onCanceled: workspace.model.endGesture()
                                }
                            }
                        }
                        Rectangle { anchors.fill: parent; radius: width/2; color: "transparent"; border.color: studio.edge }
                    }
                }
                Hint { text: editor.tr("Shift-click or check layers to select several. Drag to move and use the corner handle to resize."); Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                Hint { text: editor.tr(bridge.livePreview.active ? "Live LCD preview · unsaved profile changes." : "Draft preview · save and select it in Display to use it on the LCD."); Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            }
        }
        Panel {
            objectName: "editorPropertiesPanel"
            Layout.minimumWidth: 230; Layout.preferredWidth: Math.max(250,Math.min(380,editor.width*.30)); Layout.fillHeight: true
            ScrollView {
                id: propertiesScroll; objectName: "editorPropertiesScroll"
                anchors.fill: parent; anchors.margins: 16; rightPadding: 12; clip: true; contentWidth: availableWidth
                ColumnLayout {
                    width: propertiesScroll.availableWidth; spacing: 12
                    Copy { text: editor.tr("Properties"); font.pixelSize: 19 }
                    Hint { visible: editor.multiple; text: editor.tr("%1 layers selected").arg(workspace.model.selectionCount); Layout.fillWidth: true }
                    Hint { visible: !editor.hasSelection; text: editor.tr("Select a layer to edit it."); Layout.fillWidth: true }
                    ColumnLayout {
                        visible: editor.hasSelection; Layout.fillWidth: true; spacing: 10
                        RowLayout { Layout.fillWidth: true
                            Copy { text: editor.tr("Visible") }
                            Item { Layout.fillWidth: true }
                            Toggle { checked: editor.state.visible===true; onToggled: workspace.model.updateSelectionStyle({visible:checked}) }
                        }
                        GridLayout { visible: !editor.multiple; columns: 2; Layout.fillWidth: true
                            Hint { text: "X" } Number { to: 240-(editor.state.width || 12); value: editor.state.x || 0; objectName: "editorX"; onValueModified: workspace.model.updateSelected({x:value}) }
                            Hint { text: "Y" } Number { to: 240-(editor.state.height || 12); value: editor.state.y || 0; onValueModified: workspace.model.updateSelected({y:value}) }
                            Hint { text: editor.tr("Width") } Number { from: 12; to: 240-(editor.state.x || 0); value: editor.state.width || 12; onValueModified: workspace.model.updateSelected({width:value}) }
                            Hint { text: editor.tr("Height") } Number { from: 12; to: 240-(editor.state.y || 0); value: editor.state.height || 12; onValueModified: workspace.model.updateSelected({height:value}) }
                            Hint { text: editor.tr("Rotation") }
                            Number { objectName: "editorRotationControl"; from: 0; to: 359; stepSize: 15; value: editor.state.rotation || 0; onValueModified: workspace.model.updateSelected({rotation:value}) }
                        }
                        RowLayout { Layout.fillWidth: true
                            Tool { objectName: "rotateLayerLeft"; text: "↶ 90°"; Layout.fillWidth: true; Accessible.name: editor.tr("Rotate left"); onClicked: workspace.model.rotateSelection(-90) }
                            Tool { objectName: "rotateLayerRight"; text: "↷ 90°"; Layout.fillWidth: true; Accessible.name: editor.tr("Rotate right"); onClicked: workspace.model.rotateSelection(90) }
                        }
                        RowLayout {
                            visible: editor.multiple; Layout.fillWidth: true
                            Tool { text: "↶ 15°"; Layout.fillWidth: true; Accessible.name: editor.tr("Rotate left"); onClicked: workspace.model.rotateSelection(-15) }
                            Tool { text: "↷ 15°"; Layout.fillWidth: true; Accessible.name: editor.tr("Rotate right"); onClicked: workspace.model.rotateSelection(15) }
                        }
                        ColumnLayout { visible: !editor.multiple && editor.state.kind==="metric"; Layout.fillWidth: true
                            Hint { text: editor.tr("Reading") }
                            Choice { Layout.fillWidth: true; model: [editor.tr("CPU temperature"),editor.tr("CPU frequency"),editor.tr("GPU temperature"),editor.tr("GPU frequency")]; currentIndex: ["cpu_temp","cpu_clock","gpu_temp","gpu_clock"].indexOf(editor.state.metric); onActivated: function(index) { workspace.model.updateSelected({metric:["cpu_temp","cpu_clock","gpu_temp","gpu_clock"][index]}) } }
                            RowLayout {
                                objectName: "editorTemperatureUnits"; Layout.fillWidth: true
                                visible: editor.state.metric==="cpu_temp" || editor.state.metric==="gpu_temp"
                                Hint { text: editor.tr("Units") }
                                Item { Layout.fillWidth: true }
                                Copy { text: "°C" }
                                Toggle {
                                    id: temperatureToggle; objectName: "editorFahrenheitSwitch"; checked: workspace.temperatureUnit==="F"
                                    Accessible.name: editor.tr("Use Fahrenheit for this composition")
                                    onToggled: workspace.model.setTemperatureUnit(checked ? "F" : "C")
                                    hoverEnabled: true
                                    ToolTip {
                                        visible: temperatureToggle.hovered; delay: 400; timeout: 10000; width: 280
                                        contentItem: Hint { text: editor.tr("Applies to all temperature readings in this composition.") }
                                        background: Rectangle { radius: 8; color: studio.panel; border.color: studio.edge }
                                    }
                                }
                                Copy { text: "°F" }
                            }
                            Choice {
                                objectName: "editorTemperaturePrecision"
                                visible: editor.state.metric === "cpu_temp" || editor.state.metric === "gpu_temp"
                                Layout.fillWidth: true
                                Accessible.name: editor.tr("Temperature precision")
                                model: [editor.tr("Whole degrees"), editor.tr("1 decimal")]
                                currentIndex: workspace.temperatureDecimals
                                onActivated: function(index) { workspace.model.setTemperatureDecimals(index) }
                            }
                            Entry { text: editor.state.label || ""; placeholderText: editor.tr("Optional label"); maximumLength: 32; Layout.fillWidth: true; objectName: "layerLabelControl"; onTextEdited: workspace.model.updateSelected({label:text}) }
                        }
                        Entry { visible: !editor.multiple && editor.state.kind==="text"; text: editor.state.text || ""; maximumLength: 160; Layout.fillWidth: true; onTextEdited: workspace.model.updateSelected({text:text}) }
                        ColumnLayout { visible: !editor.multiple && (editor.state.kind==="metric" || editor.state.kind==="text"); Layout.fillWidth: true
                            Hint { text: editor.tr("Typeface") }
                            RowLayout { Layout.fillWidth: true
                                FontPicker { objectName: "systemFontControl"; studio: editor.studio; model: [editor.tr("Global typeface")].concat(bridge.systemFontLabels.slice(1)); Layout.fillWidth: true; displayText: editor.state.font_path ? bridge.fontLabel(editor.state.font_path) : editor.tr("Global typeface"); onActivated: function(index) { workspace.model.updateSelected({font_path:bridge.systemFontPath(index) || null}) } }
                                Tool { text: "↻"; enabled: !bridge.fontDiscoveryBusy; onClicked: bridge.refreshSystemFonts(); Accessible.name: editor.tr("Refresh") }
                            }
                            Tool {
                                objectName: "editorFontBrowse"; text: editor.tr("Browse…"); Layout.fillWidth: true
                                onClicked: { fontDialog.layerId = editor.state.id; fontDialog.open() }
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
                        Choice { visible: !editor.multiple && editor.state.kind==="arc"; Layout.fillWidth: true; model: [editor.tr("Comet"),editor.tr("Orbit"),editor.tr("Pulse"),editor.tr("Static")]; currentIndex: ["comet","orbit","pulse","none"].indexOf(editor.state.animation); onActivated: function(index) { workspace.model.updateSelected({animation:["comet","orbit","pulse","none"][index]}) } }
                        RowLayout {
                            visible: !editor.multiple && editor.state.kind === "effect" && !["disc","divider"].includes(editor.state.effect)
                            Layout.fillWidth: true
                            Hint { text: editor.tr("Animation"); Layout.fillWidth: true }
                            Toggle {
                                objectName: "layerEffectMotion"
                                checked: editor.state.animation !== "none"
                                Accessible.name: editor.tr("Animation")
                                onToggled: workspace.model.updateSelected({animation:checked ? "signature" : "none"})
                            }
                        }
                        RowLayout {
                            visible: editor.editingMotion && editor.state.animation !== "none"
                            Layout.fillWidth: true
                            Hint { text: editor.tr("Effect color"); Layout.fillWidth: true }
                            Choice {
                                objectName: "layerEffectStyle"
                                model: [editor.tr("Accent"),editor.tr("Rainbow")]
                                currentIndex: editor.state.effect_style === "rainbow" ? 1 : 0
                                onActivated: function(index) { workspace.model.updateSelected({effect_style:index === 1 ? "rainbow" : "accent"}) }
                            }
                        }
                        ColumnLayout {
                            visible: editor.editingMotion && editor.state.animation !== "none"; Layout.fillWidth: true
                            RowLayout {
                                Layout.fillWidth: true
                                Hint { text: editor.tr("Design animation speed"); Layout.fillWidth: true }
                                Copy { text: workspace.motionSpeed.toFixed(2) + "×" }
                            }
                            StudioSlider {
                                studio: editor.studio; objectName: "editorMotionSpeed"; Layout.fillWidth: true
                                from: .25; to: 3; stepSize: .25; value: workspace.motionSpeed
                                Accessible.name: editor.tr("Design animation speed")
                                onPressedChanged: { if (pressed) workspace.model.beginGesture(); else workspace.model.endGesture() }
                                onMoved: workspace.model.setMotionSpeed(value)
                            }
                        }
                        ColumnLayout {
                            visible: editor.editingGradient; Layout.fillWidth: true
                            Hint { text: editor.tr("Gradient style") }
                            Choice {
                                objectName: "gradientStyleControl"; Layout.fillWidth: true
                                Accessible.name: editor.tr("Gradient style")
                                model: [editor.tr("Aurora"), editor.tr("Linear"), editor.tr("Radial")]
                                currentIndex: ["aurora", "linear", "radial"].indexOf(editor.state.gradient_style)
                                onActivated: function(index) { workspace.model.updateSelected({gradient_style: ["aurora", "linear", "radial"][index]}) }
                            }
                            RowLayout {
                                visible: editor.state.gradient_style !== "radial"; Layout.fillWidth: true
                                Hint { text: editor.tr("Gradient direction") }
                                Number {
                                    objectName: "gradientDirectionControl"; to: 359; stepSize: 15
                                    value: editor.state.gradient_angle || 0
                                    Accessible.name: editor.tr("Gradient direction")
                                    onValueModified: workspace.model.updateSelected({gradient_angle: value})
                                }
                            }
                            Hint { text: editor.tr("Gradient colors") }
                            RowLayout {
                                Layout.fillWidth: true
                                Repeater {
                                    model: ["Color 1", "Color 2"]
                                    delegate: Tool {
                                        id: gradientColorButton
                                        required property string modelData
                                        required property int index
                                        readonly property string field: index === 0 ? "color" : "gradient_color"
                                        objectName: "gradient-" + field
                                        text: editor.tr(modelData)
                                        Layout.fillWidth: true
                                        contentItem: RowLayout {
                                            spacing: 6
                                            Rectangle { width: 16; height: 16; radius: 8; color: editor.state[gradientColorButton.field] || "transparent"; border.color: studio.muted }
                                            Copy { text: gradientColorButton.text; Layout.fillWidth: true }
                                        }
                                        onClicked: editor.chooseGradientColor(gradientColorButton, modelData, field)
                                    }
                                }
                            }
                        }
                        Hint { visible: workspace.model.selectionHasColor && !editor.editingGradient; text: editor.tr("Color") }
                        RowLayout { visible: workspace.model.selectionHasColor && !editor.editingGradient; spacing: 7
                            Repeater { model: ["#edf4f5","#73dfc1","#68b5ff","#ac8aff","#ff83b5","#ffb86b"]
                                delegate: Rectangle { required property string modelData; width: 24; height: 24; radius: 12; color: modelData; border.color: studio.ink; border.width: !editor.multiple && editor.state.color===modelData ? 2 : 0; MouseArea { anchors.fill: parent; onClicked: workspace.model.updateSelectionStyle({color:parent.modelData}) } }
                            }
                        }
                        Tool {
                            id: layerColorButton; objectName: "layerColorPickerButton"
                            visible: workspace.model.selectionHasColor && !editor.editingGradient
                            text: editor.tr("Choose color…"); Layout.fillWidth: true
                            contentItem: RowLayout {
                                spacing: 8
                                Rectangle { width: 16; height: 16; radius: 8; color: editor.state.color || "transparent"; border.color: studio.muted; visible: !editor.multiple }
                                Copy { text: layerColorButton.text; Layout.fillWidth: true }
                            }
                            onClicked: editor.chooseLayerColor(layerColorButton)
                        }
                        Tool { objectName: "replaceLayerMediaButton"; visible: !editor.multiple && editor.state.kind==="media"; text: editor.tr("Replace image / GIF…"); Layout.fillWidth: true; onClicked: { mediaDialog.replaceSelected=true; mediaDialog.open() } }
                        ColumnLayout {
                            visible: !editor.multiple && editor.state.kind==="media"; Layout.fillWidth: true
                            RowLayout {
                                Layout.fillWidth: true
                                Hint { text: editor.tr("Image zoom"); Layout.fillWidth: true }
                                Copy { text: Math.round((editor.state.media_zoom || 1)*100)+"%" }
                                Tool { objectName: "resetMediaZoom"; text: "100%"; Accessible.name: editor.tr("Reset image zoom"); onClicked: workspace.model.updateSelected({media_zoom:1}) }
                            }
                            StudioSlider {
                                id: mediaZoomSlider; objectName: "editorMediaZoom"; Layout.fillWidth: true
                                studio: editor.studio
                                from: 25; to: 400; stepSize: 5; value: (editor.state.media_zoom || 1)*100
                                Accessible.name: editor.tr("Image zoom")
                                onPressedChanged: { if (pressed) workspace.model.beginGesture(); else workspace.model.endGesture() }
                                onMoved: workspace.model.updateSelected({media_zoom:value/100})
                            }
                            Hint { text: editor.tr("Zoom around the image center. Enlarged edges are cropped to the layer."); Layout.fillWidth: true }
                        }
                        RowLayout {
                            visible: !editor.multiple && editor.state.kind==="media" && (editor.state.path || "").toLowerCase().endsWith(".gif")
                            Layout.fillWidth: true
                            Hint { text: editor.tr("Match GIF to output FPS"); Layout.fillWidth: true }
                            Toggle {
                                id: gifTimingToggle; objectName: "editorGifTimingSwitch"
                                checked: editor.state.gif_pacing==="smooth"; hoverEnabled: true
                                Accessible.name: editor.tr("Match GIF to output FPS")
                                onToggled: workspace.model.updateSelected({gif_pacing:checked ? "smooth" : "source"})
                                ToolTip {
                                    visible: gifTimingToggle.hovered; delay: 400; timeout: 12000; width: 300
                                    contentItem: Hint { text: editor.tr("Slows GIF frames that are faster than the output rate to reduce periodic skips. Existing playback timing is kept when disabled.") }
                                    background: Rectangle { radius: 8; color: studio.panel; border.color: studio.edge }
                                }
                            }
                        }
                        Hint { text: editor.tr("Opacity")+" · "+Math.round((editor.state.opacity===undefined ? 1 : editor.state.opacity)*100)+"%" }
                        StudioSlider {
                            objectName: "editorOpacityControl"
                            studio: editor.studio
                            from: 0; to: 1; stepSize: .05
                            value: editor.state.opacity === undefined ? 1 : editor.state.opacity
                            Layout.fillWidth: true
                            Accessible.name: editor.tr("Opacity")
                            onPressedChanged: { if (pressed) workspace.model.beginGesture(); else workspace.model.endGesture() }
                            onMoved: workspace.model.updateSelectionStyle({opacity:value})
                        }
                        Tool { text: editor.tr(editor.multiple ? "Delete selected layers" : "Delete layer"); Layout.fillWidth: true; onClicked: workspace.model.removeSelected() }
                    }
                    Hint { text: workspace.notice; visible: text.length>0; color: studio.errorColor; Layout.fillWidth: true }
                    Hint { text: bridge.fontNotice; visible: text.length>0; Layout.fillWidth: true }
                }
            }
        }
    }
    }
}
