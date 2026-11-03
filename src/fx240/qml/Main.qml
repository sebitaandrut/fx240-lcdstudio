// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1200; height: 800
    minimumWidth: 1200; minimumHeight: 760
    visible: !bridge.startMinimized; title: bridge.applicationName
    color: backgroundColor
    property int page: 0
    onPageChanged: {
        if (page!==4 && bridge.livePreview.active) { page=4; bridge.livePreview.requestEnd(); return }
        bridge.workspace.setVisible(page===4)
    }
    property color lcdAccent: bridge.initialAccent
    onLcdAccentChanged: queueSettings()
    property bool ready: false
    Component.onCompleted: ready=true
    Timer { id: settingsDebounce; interval: 200; onTriggered: bridge.applySettings(window.configuration()) }
    function tr(text) { return bridge.translate(text,bridge.language) }
    property string backgroundPath: bridge.initialBackground
    readonly property var animationKeys: ["comet","orbit","pulse","none"]

    function queueSettings() { if (ready) settingsDebounce.restart() }
    readonly property bool lightTheme: appTheme.currentIndex===1
    readonly property color backgroundColor: lightTheme ? "#eef2f4" : "#0e1216"
    readonly property color sidebar: lightTheme ? "#e5ebee" : "#12181d"
    readonly property color ink: lightTheme ? "#243139" : "#e8eef1"
    readonly property color muted: lightTheme ? "#586a74" : "#abb8c0"
    readonly property color accent: lightTheme ? "#16725e" : "#82e3c6"
    readonly property color panel: lightTheme ? "#ffffff" : "#171e24"
    readonly property color edge: lightTheme ? "#cdd8de" : "#263039"
    readonly property color controlColor: lightTheme ? "#e7edf0" : "#24323a"
    readonly property color selection: lightTheme ? "#d2e9e0" : "#223730"
    readonly property color hoverColor: lightTheme ? "#edf4f1" : "#24343a"
    readonly property color errorColor: lightTheme ? "#a72d31" : "#ffb3ad"
    readonly property color primaryFill: lightTheme ? "#9ce3cb" : "#82e3c6"
    FontLoader { id: outfit; source: bridge.uiFontUrl }
    font.family: outfit.name; font.pixelSize: 14; font.weight: Font.Normal
    font.variableAxes: ({"wght":400})
    palette.window: backgroundColor; palette.windowText: ink; palette.base: controlColor; palette.text: ink
    palette.alternateBase: panel; palette.mid: edge; palette.dark: edge; palette.light: controlColor;
    palette.toolTipBase: panel; palette.toolTipText: ink; palette.placeholderText: muted;
    palette.button: controlColor; palette.buttonText: ink
    palette.highlight: selection; palette.highlightedText: ink
    onClosing: function(close) { close.accepted = bridge.requestClose() }

    function configuration() {
        return {fps:fps.value,quality:quality.value,delay:delay.text,
                animation:animationKeys[animation.currentIndex],background:backgroundPath,backgroundDim:backgroundDim.value,font:fontPath.text,weight:weight.value,cometSpeed:cometSpeed.value,accent:lcdAccent.toString(),cometStyle:cometStyle.currentIndex===1 ? "rainbow" : "accent",temperatureUnit:temperatureUnit.currentIndex===1 ? "F" : "C",decimals:decimals.checked,device:device.currentText}
    }
    function valueAt(index) { return bridge.sensorRows.length > index ? bridge.sensorRows[index].target : "N/A" }
    function changeProfile(index) {
        if (index === 0) { fps.value=24; quality.value=65; delay.text="2" }
        if (index === 1) { fps.value=5; quality.value=85; delay.text="10" }
    }
    component Caption: Label { textFormat: Text.PlainText; color: window.muted; font.pixelSize: 14 }
    component Rule: Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: window.edge }
    component SvgIcon: Image {
        property string name: "monitor"
        property string role: "muted"
        width: 19; height: 19
        source: "../assets/icons/"+(window.lightTheme ? "light/" : "dark/")+name+"-"+role+".svg"
        sourceSize.width: 24; sourceSize.height: 24
    }
    component NavButton: Button {
        property string iconName: "monitor"
        property bool selected: false
        Layout.fillWidth: true; implicitHeight: 44
        contentItem: RowLayout {
            spacing: 12
            SvgIcon { name: parent.parent.iconName; role: parent.parent.selected ? "accent" : "muted"; opacity: parent.parent.enabled ? 1 : .4 }
            Label { textFormat: Text.PlainText; text: parent.parent.text; color: parent.parent.selected ? window.accent : window.muted; opacity: parent.parent.enabled ? 1 : .4; Layout.fillWidth: true }
        }
        leftPadding: 13; rightPadding: 13
        background: Rectangle { radius: 9; color: parent.selected ? window.selection : parent.hovered ? window.hoverColor : "transparent" }
    }
    component Action: Button {
        property string iconName: "play"
        property bool primary: false
        implicitHeight: 40
        leftPadding: 16; rightPadding: 16
        contentItem: RowLayout {
            spacing: 8
            SvgIcon { name: parent.parent.iconName; role: parent.parent.primary ? "action" : "muted"; opacity: parent.parent.enabled ? 1 : .35 }
            Label { textFormat: Text.PlainText; text: parent.parent.text; color: parent.parent.primary ? "#08271e" : window.ink; opacity: parent.parent.enabled ? 1 : .4; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
        }
        background: Rectangle { radius: 9; color: parent.primary ? window.primaryFill : window.controlColor; opacity: parent.enabled ? 1 : .35; border.color: window.edge; border.width: parent.primary ? 0 : 1 }
    }
    component Choice: ComboBox {
        id: choice
        property bool translated: true
        implicitHeight: 32
        background: Rectangle { color: window.controlColor; radius: 7; border.color: window.edge }
        contentItem: Text { text: choice.translated ? window.tr(choice.displayText) : choice.displayText; textFormat: Text.PlainText; font: choice.font; color: window.ink; verticalAlignment: Text.AlignVCenter; leftPadding: 12; rightPadding: 30; elide: Text.ElideRight }
        indicator: Text { x: choice.width-25; y: (choice.height-height)/2; text: "⌄"; font.pixelSize: 16; color: window.muted }
        delegate: ItemDelegate {
            required property var modelData
            required property int index
            width: choice.width-8; height: 32
            highlighted: choice.highlightedIndex===index
            background: Rectangle { radius: 5; color: parent.highlighted ? window.selection : parent.hovered ? window.hoverColor : "transparent" }
            contentItem: Text { text: choice.translated ? window.tr(parent.modelData) : parent.modelData; textFormat: Text.PlainText; color: parent.highlighted ? window.accent : window.ink; font: choice.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        }
        popup: Popup {
            objectName: choice.objectName+"Popup"
            y: choice.height+5; width: choice.width; padding: 4; margins: 12
            implicitHeight: Math.min(contentItem.implicitHeight+8,240)
            background: Rectangle { color: window.panel; radius: 9; border.color: window.edge }
            contentItem: ListView {
                clip: true; implicitHeight: contentHeight
                model: choice.popup.visible ? choice.delegateModel : null
                currentIndex: choice.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator {}
            }
        }
    }
    component SmallButton: Button {
        implicitHeight: 32
        background: Rectangle { color: parent.hovered ? window.hoverColor : window.controlColor; radius: 7; border.color: window.edge }
    }
    component InfoLabel: RowLayout {
        id: info
        property string text: ""
        property string help: ""
        spacing: 6
        Caption { text: window.tr(info.text) }
        ToolButton {
            id: helpButton; objectName: "infoHelpButton"; implicitWidth: 18; implicitHeight: 18; hoverEnabled: true
            Accessible.name: window.tr(info.help)
            background: Rectangle { radius: 9; color: "transparent"; border.color: window.muted }
            contentItem: Text { text: "i"; color: window.muted; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            ToolTip {
                id: helpTip; objectName: "infoTooltip"
                visible: helpButton.hovered || helpButton.activeFocus
                delay: 400; timeout: 12000; width: 320
                text: window.tr(info.help)
                contentItem: Text { text: helpTip.text; font.pixelSize: 14; color: window.ink; wrapMode: Text.WordWrap }
                background: Rectangle { radius: 8; color: window.panel; border.color: window.edge }
            }
        }
    }
    component SensorCard: Rectangle {
        id: sensorCard
        property string componentName: "CPU"
        property string degrees: "N/A"
        property string clock: "N/A"
        Layout.fillWidth: true; implicitHeight: width<220 ? 92 : 68; radius: 13; color: window.panel; border.color: window.edge
        ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 3
            Caption { text: parent.parent.componentName; font.letterSpacing: 1 }
            GridLayout { columns: sensorCard.width<220 ? 1 : 2; Layout.fillWidth: true; rowSpacing: 0
                Label { textFormat: Text.PlainText; text: sensorCard.degrees; color: window.ink; font.pixelSize: 26; Layout.fillWidth: true }
                Caption { text: sensorCard.clock; font.pixelSize: 14 }
            }
        }
    }
    Popup {
        id: accentPicker; objectName: "accentPicker"
        parent: Overlay.overlay
        popupType: Popup.Item
        width: 320; padding: 16; focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        property real hue: 0.45
        property real saturation: 0.6
        property real brightness: 0.9
        property bool syncing: false
        property bool editingReady: false
        function positionNearAnchor() {
            var point=customAccent.mapToItem(accentPicker.parent,0,customAccent.height)
            x=Math.max(12,Math.min(point.x+customAccent.width-accentPicker.width,window.width-accentPicker.width-12))
            y=Math.max(12,Math.min(point.y+8,window.height-accentPicker.height-12))
        }
        onOpened: positionNearAnchor()
        onHeightChanged: { if (editingReady) positionNearAnchor() }
        Connections {
            target: window
            function onWidthChanged() { if (accentPicker.visible) accentPicker.positionNearAnchor() }
            function onHeightChanged() { if (accentPicker.visible) accentPicker.positionNearAnchor() }
        }
        function readColor() {
            var color=window.lcdAccent
            if (color.hsvHue>=0) hue=color.hsvHue
            saturation=color.hsvSaturation
            brightness=color.hsvValue
        }
        function publishColor() {
            if (!editingReady || syncing) return
            window.lcdAccent=Qt.hsva(hue,saturation,brightness,1)
            hexColor.text=window.lcdAccent.toString().toUpperCase()
        }
        function applyHex() {
            if (!hexColor.acceptableInput) return
            syncing=true
            window.lcdAccent=hexColor.text
            readColor()
            syncing=false
        }
        onHueChanged: publishColor()
        onSaturationChanged: publishColor()
        onBrightnessChanged: publishColor()
        onAboutToShow: {
            syncing=true; readColor()
            hexColor.text=window.lcdAccent.toString().toUpperCase()
            syncing=false; editingReady=true
            positionNearAnchor()
        }
        onClosed: editingReady=false
        background: Rectangle { color: window.panel; radius: 12; border.color: window.edge }
        contentItem: ColumnLayout {
            spacing: 10
            RowLayout {
                Label { textFormat: Text.PlainText; text: window.tr("Custom accent"); color: window.ink; font.pixelSize: 17 }
                Item { Layout.fillWidth: true }
                SmallButton { text: window.tr("Done"); onClicked: accentPicker.close() }
            }
            Rectangle {
                id: saturationValue; objectName: "accentSaturationValue"
                Layout.fillWidth: true; implicitHeight: 132; radius: 7
                color: Qt.hsva(accentPicker.hue,1,1,1)
                Rectangle { anchors.fill: parent; radius: 7; gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#ffffff" } GradientStop { position: 1; color: "#00ffffff" } } }
                Rectangle { anchors.fill: parent; radius: 7; gradient: Gradient { GradientStop { position: 0; color: "#00000000" } GradientStop { position: 1; color: "#000000" } } }
                Rectangle {
                    width: 14; height: 14; radius: 7; color: "transparent"; border.color: "#ffffff"; border.width: 2
                    x: Math.max(0,Math.min(parent.width-width,accentPicker.saturation*parent.width-width/2))
                    y: Math.max(0,Math.min(parent.height-height,(1-accentPicker.brightness)*parent.height-height/2))
                    Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 5; color: "transparent"; border.color: "#243139" }
                }
                MouseArea {
                    anchors.fill: parent
                    function selectPoint(point) {
                        accentPicker.saturation=Math.max(0,Math.min(1,point.x/width))
                        accentPicker.brightness=1-Math.max(0,Math.min(1,point.y/height))
                    }
                    onPressed: function(mouse) { selectPoint(mouse) }
                    onPositionChanged: function(mouse) { if (pressed) selectPoint(mouse) }
                }
            }
            Caption { text: window.tr("Hue") }
            Slider {
                id: hueControl; objectName: "accentHueControl"
                from: 0; to: 1; stepSize: 0.001; value: accentPicker.hue
                Layout.fillWidth: true; implicitHeight: 20; Accessible.name: window.tr("Hue")
                onMoved: accentPicker.hue=value
                background: Rectangle {
                    x: hueControl.leftPadding; y: hueControl.topPadding+(hueControl.availableHeight-height)/2
                    width: hueControl.availableWidth; height: 8; radius: 4
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "#ff0000" }
                        GradientStop { position: 0.167; color: "#ffff00" }
                        GradientStop { position: 0.333; color: "#00ff00" }
                        GradientStop { position: 0.5; color: "#00ffff" }
                        GradientStop { position: 0.667; color: "#0000ff" }
                        GradientStop { position: 0.833; color: "#ff00ff" }
                        GradientStop { position: 1; color: "#ff0000" }
                    }
                }
                handle: Rectangle { x: hueControl.leftPadding+hueControl.visualPosition*(hueControl.availableWidth-width); y: hueControl.topPadding+(hueControl.availableHeight-height)/2; width: 14; height: 14; radius: 7; color: "#ffffff"; border.color: "#243139" }
            }
            RowLayout {
                Rectangle { implicitWidth: 30; implicitHeight: 30; radius: 6; color: window.lcdAccent; border.color: window.edge }
                TextField {
                    id: hexColor; objectName: "accentHexControl"
                    Layout.fillWidth: true; implicitHeight: 32; maximumLength: 7
                    selectByMouse: true; Accessible.name: window.tr("Hex color")
                    validator: RegularExpressionValidator { regularExpression: /^#[0-9a-fA-F]{6}$/ }
                    onTextEdited: accentPicker.applyHex()
                    onAccepted: { accentPicker.applyHex(); accentPicker.close() }
                    background: Rectangle { color: window.controlColor; radius: 7; border.color: hexColor.acceptableInput ? window.edge : window.errorColor }
                }
            }
            Caption { text: window.tr("Use #RRGGBB"); visible: !hexColor.acceptableInput; color: window.errorColor }
        }
    }
    Dialog {
        id: preferenceDialog; objectName: "preferenceDialog"
        parent: Overlay.overlay; popupType: Popup.Item
        modal: true; focus: true; width: Math.min(560,window.width-48)
        x: (window.width-width)/2; y: (window.height-height)/2
        Connections { target: bridge; function onChanged() { if (preferenceDialog.visible && !bridge.preferenceNotice) preferenceDialog.close() } }
        title: window.tr("Preferences notice")
        header: Label { textFormat: Text.PlainText; text: preferenceDialog.title; color: window.ink; font.pixelSize: 18; leftPadding: 20; rightPadding: 20; topPadding: 18; bottomPadding: 8 }
        palette.window: window.panel; palette.windowText: window.ink
        background: Rectangle { color: window.panel; radius: 12; border.color: window.edge }
        contentItem: ColumnLayout { spacing: 16
            ScrollView { Layout.fillWidth: true; Layout.preferredHeight: Math.min(300,detailsText.implicitHeight); contentWidth: availableWidth
                TextArea { textFormat: TextEdit.PlainText; id: detailsText; text: bridge.preferenceDetails; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: window.ink; background: Item {} }
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                SmallButton { text: window.tr("Retry saving"); visible: bridge.preferenceCanRetry; onClicked: { bridge.flushPreferences(); if (!bridge.preferenceNotice) preferenceDialog.close() } }
                SmallButton { text: window.tr("Close"); onClicked: preferenceDialog.close() }
            }
        }
    }
    AssetPicker {
        id: fontDialog; objectName: "fontAssetPicker"; studio: window; kind: "font"; initialPath: fontPath.text
        onSelected: function(file) { fontPath.text=bridge.localPath(file) }
    }
    AssetPicker {
        id: backgroundDialog; objectName: "backgroundAssetPicker"; studio: window; initialPath: window.backgroundPath
        onSelected: function(file) { window.backgroundPath=bridge.localPath(file); window.queueSettings() }
    }


    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.preferredWidth: 180; Layout.fillHeight: true; color: window.sidebar
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 10
                RowLayout { spacing: 10; Layout.topMargin: 10; Layout.fillWidth: true
                    Image { objectName: "brandIcon"; source: bridge.brandIconBase+(window.lightTheme ? "tray-lcd-light.svg" : "tray-lcd-dark.svg"); Layout.preferredWidth: 30; Layout.preferredHeight: 30; Layout.alignment: Qt.AlignVCenter; sourceSize.width: 60; sourceSize.height: 60; fillMode: Image.PreserveAspectFit; Accessible.ignored: true }
                    ColumnLayout { spacing: 1
                        Label { objectName: "brandTitle"; text: "FX240"; color: window.ink; font.pixelSize: 28 }
                        Caption { objectName: "brandSubtitle"; text: "LCD STUDIO"; font.pixelSize: 14; font.letterSpacing: 1 }
                    }
                }
                Item { Layout.preferredHeight: 26 }
                NavButton { text: window.tr("Appearance"); iconName: "monitor"; selected: window.page===0 || window.page===4; onClicked: window.page=0 }
                NavButton { text: window.tr("Sensors"); iconName: "activity"; selected: window.page===1; onClicked: window.page=1 }
                Item { Layout.fillHeight: true }
                NavButton { text: window.tr("Diagnostics"); iconName: "chart-line"; selected: window.page===2; onClicked: window.page=2 }
                NavButton { text: window.tr("Settings"); iconName: "settings-2"; selected: window.page===3; onClicked: window.page=3 }
                Rule {}
                Caption { text: window.tr("Experimental / v0.1.0"); font.pixelSize: 14 }
            }
        }
        ColumnLayout {
            objectName: "outputCard"
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 20; spacing: 12
            RowLayout {
                ColumnLayout { spacing: 4
                    Label { textFormat: Text.PlainText; text: window.tr(["Appearance","Sensors","Diagnostics","Settings","Appearance"][window.page]); color: window.ink; font.pixelSize: 26 }
                    Caption { text: window.tr(["Your designs and their appearance, in one workspace.","The selected CPU and GPU readings.","Inspect the same sample and frame used by output.","Language, startup and transmission settings.","Arrange your own LCD composition."][window.page]) }
                }
                Item { Layout.fillWidth: true }
                SmallButton { text: window.tr("Hide to tray"); visible: bridge.trayAvailable; onClicked: bridge.minimizeToTray() }
                Choice { id: appTheme; objectName: "appThemeControl"; model: ["Dark","Light"]; currentIndex: bridge.uiTheme==="light" ? 1 : 0; onCurrentIndexChanged: { if (window.ready) bridge.setUiTheme(currentIndex===1 ? "light" : "dark") } Layout.preferredWidth: 110; Accessible.name: window.tr("Application theme") }
            }
            ScrollView {
                id: pageScroll; objectName: "pageScroll"
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth
                StackLayout {
                width: pageScroll.availableWidth
                height: window.page===4 ? Math.max(460,pageScroll.availableHeight) : window.page===0 ? Math.max(520,pageScroll.availableHeight) : window.page===3 ? settingsPane.implicitHeight : 580
                currentIndex: window.page
                GridLayout {
                    id: appearanceWorkspace; objectName: "appearanceWorkspace"
                    columns: bridge.activeContentIndex===0 ? 3 : 2; columnSpacing: 12; rowSpacing: 12
                    Rectangle {
                        Layout.preferredWidth: 184; Layout.fillHeight: true
                        radius: 16; color: window.panel; border.color: window.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 14; spacing: 12
                            Label { text: window.tr("Designs"); color: window.ink; font.pixelSize: 20 }
                            Caption { text: window.tr("Built-in and saved"); wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            ListView {
                                id: designs; objectName: "designLibrary"
                                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                                model: bridge.contentLabels
                                delegate: Button {
                                    required property string modelData
                                    required property int index
                                    width: designs.width; height: 52
                                    contentItem: Label { text: parent.modelData; textFormat: Text.PlainText; color: parent.index===bridge.activeContentIndex ? window.accent : window.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                    background: Rectangle { radius: 8; color: parent.index===bridge.activeContentIndex ? window.selection : parent.hovered ? window.hoverColor : window.controlColor }
                                    onClicked: bridge.selectContent(index)
                                }
                            }
                            Caption { text: bridge.profileNotice; visible: text.length>0; color: window.errorColor; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 17; color: window.panel; border.color: window.edge
                            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 12
                                RowLayout {
                                    Label { text: window.tr("Preview"); color: window.accent; font.pixelSize: 16 }
                                    Item { Layout.fillWidth: true }
                                    SmallButton { objectName: "openEditorButton"; text: window.tr("Editor"); onClicked: { window.page=4; bridge.editActive() } }
                                }
                                Caption { text: bridge.activeContentName; Layout.alignment: Qt.AlignHCenter }
                                Item { Layout.fillHeight: true }
                                Image { objectName: "framePreview"; source: bridge.previewUrl; cache: false; smooth: true; fillMode: Image.PreserveAspectFit; Layout.preferredWidth: Math.min(320,parent.width); Layout.preferredHeight: width; Layout.alignment: Qt.AlignHCenter }
                                Item { Layout.fillHeight: true }
                                Caption { text: "240 × 240"; Layout.alignment: Qt.AlignHCenter }
                            }
                        }
                        RowLayout { Layout.fillWidth: true; spacing: 10
                            SensorCard { componentName: "CPU"; degrees: window.valueAt(0); clock: window.valueAt(1) }
                            SensorCard { componentName: "GPU"; degrees: window.valueAt(2); clock: window.valueAt(3) }
                        }
                    }
                    ColumnLayout {
                        objectName: "focusInspector"; visible: bridge.activeContentIndex===0
                        Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: Math.max(310,Math.min(420,window.width*.28)); Layout.maximumWidth: 420; Layout.fillHeight: true
                        Rectangle {
                            visible: bridge.activeContentIndex===0; Layout.fillWidth: true; Layout.fillHeight: true; Layout.alignment: Qt.AlignTop; radius: 17; color: window.panel; border.color: window.edge
                            ScrollView { id: appearanceScroll; objectName: "focusPropertiesScroll"; rightPadding: 14
                            anchors.fill: parent; anchors.margins: 18; clip: true
                            contentWidth: availableWidth
                            ColumnLayout { objectName: "focusPropertiesContent"; width: appearanceScroll.availableWidth; spacing: 12
                                RowLayout { Layout.fillWidth: true;
                                    Label { textFormat: Text.PlainText; text: window.tr("Customize Focus"); color: window.ink; font.pixelSize: 20 }
                                    Item { Layout.fillWidth: true }

                                }
                                Rule {}
                                Caption { text: window.tr("LCD accent") }
                                RowLayout { Layout.fillWidth: true; spacing: 8
                                Flow { objectName: "accentPalette"; Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 8
                                    Repeater { model: ["#73dfc1","#68b5ff","#ac8aff","#ff83b5","#ffb86b","#f1f5f9"]
                                        delegate: Button {
                                            required property string modelData
                                            objectName: "accentSwatch-"+modelData
                                            implicitWidth: 22; implicitHeight: 32
                                            Accessible.name: window.tr("LCD accent ")+modelData
                                            background: Rectangle { width: 22; height: 22; anchors.centerIn: parent; radius: 11; color: parent.modelData; border.width: window.lcdAccent.toString()===parent.modelData ? 3 : 0; border.color: window.lightTheme ? "#243139" : "#ffffff" }
                                            onClicked: window.lcdAccent=modelData
                                            ToolTip.visible: hovered; ToolTip.text: modelData.toUpperCase()
                                        }
                                    }
                                }
                                    SmallButton { id: customAccent; objectName: "customAccentButton"; text: window.tr("Custom"); Layout.minimumWidth: 0; Layout.preferredWidth: Math.min(150,appearanceScroll.availableWidth*.48); Layout.alignment: Qt.AlignVCenter; onClicked: accentPicker.open() }
                                }
                                RowLayout { Layout.fillWidth: true;
                                    Caption { text: window.tr("Animation") }
                                    Item { Layout.fillWidth: true }
                                    Choice { id: animation; objectName: "animationControl"; model: ["Comet","Orbit","Pulse","Static"]; currentIndex: Math.max(0,window.animationKeys.indexOf(bridge.initialAnimation)); Layout.minimumWidth: 0; Layout.preferredWidth: Math.min(150,appearanceScroll.availableWidth*.48); onActivated: window.queueSettings() }
                                }
                                RowLayout { Layout.fillWidth: true;
                                    Caption { text: window.tr("Effect color") }
                                    Item { Layout.fillWidth: true }
                                    Choice { id: cometStyle; objectName: "cometStyleControl"; enabled: animation.currentIndex!==3; model: ["Accent","Rainbow"]; currentIndex: bridge.initialCometStyle==="rainbow" ? 1 : 0; Layout.minimumWidth: 0; Layout.preferredWidth: Math.min(150,appearanceScroll.availableWidth*.48); onCurrentIndexChanged: window.queueSettings() }
                                }
                                RowLayout { Layout.fillWidth: true; spacing: 12
                                    Caption { text: window.tr("Speed") }
                                    Slider {
                                        id: cometSpeed; objectName: "cometSpeedControl"
                                        enabled: animation.currentIndex!==3
                                        from: 0.25; to: 3; stepSize: 0.25; value: bridge.initialCometSpeed
                                        Layout.fillWidth: true; Layout.minimumWidth: 30; implicitHeight: 24
                                        onValueChanged: window.queueSettings(); Accessible.name: window.tr("Comet speed")
                                        background: Rectangle { x: cometSpeed.leftPadding; y: cometSpeed.topPadding+cometSpeed.availableHeight/2-2; width: cometSpeed.availableWidth; height: 4; radius: 2; color: window.edge
                                            Rectangle { width: parent.width*cometSpeed.visualPosition; height: 4; radius: 2; color: window.accent }
                                        }
                                        handle: Rectangle { x: cometSpeed.leftPadding+cometSpeed.visualPosition*(cometSpeed.availableWidth-width); y: cometSpeed.topPadding+(cometSpeed.availableHeight-height)/2; width: 14; height: 14; radius: 7; color: window.ink }
                                    }
                                    Label { textFormat: Text.PlainText; text: cometSpeed.value.toFixed(2)+"×"; color: window.ink; Layout.preferredWidth: 48; horizontalAlignment: Text.AlignRight }
                                }
                                RowLayout { Layout.fillWidth: true;
                                    InfoLabel { text: window.tr("Units"); help: "Raw sensor temperatures remain Celsius. Display conversion affects the LCD, preview, and target readings only." }
                                    Item { Layout.fillWidth: true }
                                    Choice { id: temperatureUnit; objectName: "temperatureUnitControl"; model: ["°C","°F"]; currentIndex: bridge.initialTemperatureUnit==="F" ? 1 : 0; Layout.minimumWidth: 0; Layout.preferredWidth: Math.min(150,appearanceScroll.availableWidth*.48); onCurrentIndexChanged: window.queueSettings() }
                                }
                                Rule {}
                                RowLayout { Layout.fillWidth: true;
                                    Caption { text: window.tr("Temperature") }
                                    Item { Layout.fillWidth: true }
                                    Choice { id: decimals; objectName: "decimalControl"; property bool checked: currentIndex===1; model: ["Whole degrees","1 decimal"]; currentIndex: bridge.initialDecimals ? 1 : 0; Layout.minimumWidth: 0; Layout.preferredWidth: Math.min(150,appearanceScroll.availableWidth*.48); onCurrentIndexChanged: window.queueSettings() }
                                }
                                GridLayout { columns: 1; Layout.fillWidth: true; rowSpacing: 8
                            InfoLabel { text: window.tr("Installed fonts"); help: "Discover local scalable TTF/OTF fonts by family and style. Nothing is uploaded. Collections are not listed." }
                            RowLayout { Layout.fillWidth: true;
                                FontPicker { studio: window; objectName: "systemFontControl"; model: bridge.systemFontLabels; Layout.fillWidth: true; displayText: currentIndex>0 ? currentText : fontPath.text ? window.tr("Custom font file") : window.tr("Bundled Outfit (default)"); onActivated: function(index) { fontPath.text=bridge.systemFontPath(index) } }
                                SmallButton { text: "↻"; Accessible.name: window.tr("Refresh"); implicitWidth: 32; enabled: !bridge.fontDiscoveryBusy; onClicked: bridge.refreshSystemFonts() }
                            }
                            Caption { text: bridge.fontNotice; visible: text.length>0; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.columnSpan: 1 }
                            InfoLabel { text: window.tr("Typeface file"); help: "Use a local TrueType font or leave this empty for bundled Outfit. A missing font is rejected without interrupting output." }
                            RowLayout { Layout.fillWidth: true; TextField { color: window.ink; placeholderTextColor: window.muted; background: Rectangle { radius: 7; color: window.controlColor; border.color: window.edge } id: fontPath; Layout.minimumWidth: 0; Layout.preferredWidth: 120; onTextChanged: window.queueSettings(); text: bridge.initialFont; placeholderText: window.tr("Bundled Outfit (default)"); Layout.fillWidth: true } SmallButton { text: window.tr("Browse…"); onClicked: fontDialog.open() } }
                            InfoLabel { text: window.tr("Variable font weight"); help: "Changes the weight of variable fonts from 100 to 900. Static fonts keep their original weight." }
                            StudioNumber { studio: window; id: weight; enabled: bridge.globalFontInfo.variable===true; objectName: "weightControl"; onValueChanged: window.queueSettings(); from: 100; to: 900; stepSize: 50; value: bridge.initialWeight; editable: true; Layout.fillWidth: true }
                                }

                                Rule {}
                                RowLayout { Layout.fillWidth: true;
                                    InfoLabel { text: window.tr("Background"); help: "Local image or GIF behind the readings. Up to 120 frames; files stay on this computer." }
                                    Item { Layout.fillWidth: true }
                                    SmallButton { objectName: "backgroundChoose"; text: window.tr(window.backgroundPath ? "Change…" : "Choose…"); onClicked: backgroundDialog.open() }
                                    SmallButton { text: window.tr("Clear"); enabled: window.backgroundPath.length>0; onClicked: { window.backgroundPath=""; window.queueSettings() } }
                                }
                                RowLayout { Layout.fillWidth: true;
                                    Caption { text: window.tr("Dimming") }
                                    Slider { id: backgroundDim; objectName: "backgroundDimControl"; from: 0; to: 0.9; stepSize: .05; value: bridge.initialBackgroundDim; Layout.fillWidth: true; enabled: window.backgroundPath.length>0; onMoved: window.queueSettings() }
                                    Caption { text: Math.round(backgroundDim.value*100)+"%"; Layout.preferredWidth: 40; horizontalAlignment: Text.AlignRight }
                                }
                        Caption { visible: bridge.globalFontInfo.variable!==true; text: window.tr("Static font: select an installed style to change its weight."); wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            }
                            }
                        }


                    }
                }
                Rectangle {
                    radius: 17; color: window.panel; border.color: window.edge
                    ColumnLayout { anchors.fill: parent; anchors.margins: 24; spacing: 18
                        Label { textFormat: Text.PlainText; text: window.tr("Selected readings"); color: window.ink; font.pixelSize: 22 }
                        Caption { text: window.tr("Labels and sources are shown exactly as supplied by Linux. Sensor selection is automatic in this version."); wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Repeater { model: bridge.sensorRows
                            delegate: ColumnLayout { required property var modelData; Layout.fillWidth: true; spacing: 8
                                RowLayout { Label { textFormat: Text.PlainText; text: window.tr(modelData.label); color: window.ink; font.pixelSize: 17 } Item { Layout.fillWidth: true } Label { textFormat: Text.PlainText; text: modelData.target; color: window.accent; font.pixelSize: 26 } }
                                Caption { text: window.tr(modelData.source); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                                Rule {}
                            }
                        }
                        Item { Layout.fillHeight: true }
                        Caption { text: bridge.sampleLabel }
                    }
                }
                Rectangle {
                    radius: 17; color: window.panel; border.color: window.edge
                    ColumnLayout { anchors.fill: parent; anchors.margins: 24; spacing: 18
                        Label { textFormat: Text.PlainText; text: window.tr("Sensor comparison"); color: window.ink; font.pixelSize: 22 }
                        Caption { text: bridge.sampleLabel; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        RowLayout { Caption { text: window.tr("SENSOR"); Layout.fillWidth: true } Caption { text: window.tr("RAW SAMPLE"); Layout.preferredWidth: 160 } Caption { text: window.tr("LCD TARGET"); Layout.preferredWidth: 120 } }
                        Repeater { model: bridge.sensorRows
                            delegate: RowLayout { required property var modelData; Layout.fillWidth: true
                                Label { textFormat: Text.PlainText; text: window.tr(modelData.label); color: window.ink; Layout.fillWidth: true }
                                Label { textFormat: Text.PlainText; text: modelData.raw; color: window.ink; Layout.preferredWidth: 160 }
                                Label { textFormat: Text.PlainText; text: modelData.target; color: window.accent; font.pixelSize: 20; Layout.preferredWidth: 120 }
                            }
                        }
                        Rule {}
                        Caption { text: bridge.sleepStatus; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Caption { text: bridge.shutdownStatus; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Caption { text: bridge.standbyFallbackStatus; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Caption { text: bridge.statistics; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Caption { text: window.tr("One sample feeds the LCD and preview. Sensors refresh at 1 Hz; numeric values update directly. Host timing does not measure physical LCD refresh."); wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Item { Layout.fillHeight: true }
                    }
                }
                Rectangle {
                    id: settingsPane
                    radius: 17; color: window.panel; border.color: window.edge
                    implicitHeight: settingsContent.implicitHeight+48
                    ColumnLayout {
                        id: settingsContent
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 24; spacing: 16
                        Label { textFormat: Text.PlainText; text: window.tr("General settings"); color: window.ink; font.pixelSize: 22 }
                        Caption { text: window.tr("Changes are saved automatically.") }
                        GridLayout { columns: 2; Layout.fillWidth: true; columnSpacing: 20; rowSpacing: 12
                            InfoLabel { text: window.tr("Language"); help: "Choose the interface language. Sensor labels and paths from Linux are not translated." }
                            Choice { id: languageChoice; objectName: "languageControl"; model: ["English","Español"]; currentIndex: bridge.language==="es" ? 1 : 0; onCurrentIndexChanged: { if (window.ready) bridge.setLanguage(currentIndex===1 ? "es" : "en") } Layout.fillWidth: true }
                            InfoLabel { text: window.tr("Start at login"); help: "Start minimized after graphical login. Without a system tray, the window stays in the taskbar. Moving the executable requires enabling this again." }
                            Choice { objectName: "autostartControl"; model: [window.tr("Disabled"),window.tr("Minimized in tray")]; currentIndex: bridge.autostartEnabled ? 1 : 0; enabled: bridge.autostartSupported; onActivated: function(index) { bridge.setAutostart(index===1) }; Layout.fillWidth: true }
                            InfoLabel { text: window.tr("Output preset"); help: "Presets adjust frame rate, JPEG quality, and report delay together. Custom values remain available below." }
                            Choice { model: ["Smooth · 24 FPS","Conservative · 5 FPS","Custom"]; currentIndex: fps.value===24 && quality.value===65 && Number(delay.text)===2 ? 0 : fps.value===5 && quality.value===85 && Number(delay.text)===10 ? 1 : 2; onActivated: function(index) { window.changeProfile(index) }; Layout.fillWidth: true }
                        }
                        SmallButton { objectName: "advancedToggle"; text: advancedSettings.visible ? window.tr("Hide advanced settings") : window.tr("Show advanced settings"); onClicked: advancedSettings.visible=!advancedSettings.visible }
                        GridLayout { id: advancedSettings; objectName: "advancedSettings"; visible: false; columns: 2; Layout.fillWidth: true; columnSpacing: 20; rowSpacing: 12
                            InfoLabel { text: "LCD device"; help: "The USB device must match FX240 identity. Pause LCD output before changing it. Device paths are rediscovered at startup." }
                            RowLayout { Choice { id: device; enabled: !bridge.sending; onActivated: window.queueSettings(); objectName: "deviceControl"; model: bridge.devices; Component.onCompleted: { if (bridge.initialDevice) currentIndex=find(bridge.initialDevice) } Layout.fillWidth: true } SmallButton { text: window.tr("Refresh"); onClicked: bridge.refreshDevices() } }
                            InfoLabel { text: "Frame rate"; help: "Limits generated frames per second, up to 24. This does not measure the physical LCD refresh rate." }
                            StudioNumber { studio: window; id: fps; onValueChanged: window.queueSettings(); objectName: "fpsControl"; from: 1; to: 24; value: bridge.initialFps; editable: true; Layout.fillWidth: true }
                            InfoLabel { text: "JPEG quality"; help: "Higher quality can increase image detail and USB payload size. Range: 1 to 95." }
                            StudioNumber { studio: window; id: quality; onValueChanged: window.queueSettings(); from: 1; to: 95; value: bridge.initialQuality; editable: true; Layout.fillWidth: true }
                            InfoLabel { text: "Inter-report delay (ms)"; help: "Pause between HID reports in milliseconds. Lower values may improve transmission time but require hardware validation." }
                            TextField { color: window.ink; background: Rectangle { radius: 7; color: window.controlColor; border.color: window.edge } id: delay; onTextChanged: window.queueSettings(); text: bridge.initialDelay; Layout.fillWidth: true }
                        }
                    }
                }
                EditorPane { studio: window }
            }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: 64; radius: 12; color: window.panel; border.color: window.edge
                RowLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 12
                    Rectangle { Layout.alignment: Qt.AlignVCenter; width: 7; height: 7; radius: 3.5; color: bridge.sending ? window.accent : window.muted }
                    Label { Layout.alignment: Qt.AlignVCenter; objectName: "outputStatus"; text: bridge.status; color: window.ink }
                    Item { Layout.fillWidth: true }
                    Caption { Layout.alignment: Qt.AlignVCenter; text: fps.value+window.tr(" FPS target"); font.pixelSize: 14 }
                    Action { Layout.alignment: Qt.AlignVCenter; objectName: "stopButton"; text: window.tr("Stop display"); iconName: "square"; visible: bridge.sending; enabled: bridge.sending; onClicked: bridge.stopOutput() }

                    Action { Layout.alignment: Qt.AlignVCenter; objectName: "sendButton"; text: window.tr("Start display"); primary: true; visible: !bridge.sending; enabled: !bridge.sending && device.currentText.length>0; onClicked: bridge.startOutput(window.configuration()) }
                }
            }
            Rectangle {
                objectName: "preferenceBanner"; visible: bridge.preferenceNotice.length>0
                Layout.fillWidth: true; implicitHeight: Math.max(48,noticeText.implicitHeight+20)
                color: window.selection; radius: 8
                RowLayout { anchors.fill: parent; anchors.margins: 10; spacing: 12
                    Rectangle { width: 18; height: 18; radius: 9; color: "transparent"; border.color: window.accent; Label { anchors.centerIn: parent; text: "i"; font.pixelSize: 12; color: window.accent } }
                    Label { id: noticeText; text: bridge.preferenceNotice; color: window.ink; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    SmallButton { objectName: "preferenceDetailsButton"; text: window.tr("Details"); onClicked: preferenceDialog.open() }
                }
            }
            Caption { objectName: "outputError"; text: bridge.runtimeError; visible: text.length>0; color: window.errorColor; wrapMode: Text.Wrap; Layout.fillWidth: true }

        }
    }
}
