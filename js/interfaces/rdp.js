// RDP related
var rdp_events = {};
var mouse_to_rdp = {
    0: 1,
    1: 3,
    2: 2
}

var rdp_specialchar_to_name = {
    'Backspace': '14', //'VK_BACK',
    'Escape': 'VK_ESCAPE',
    'Tab': '15',
    'Enter': 'VK_RETURN',
    'Insert': 'VK_INSERT',
    'Delete': 'VK_DELETE',
    'Home': 'VK_HOME',
    'End': 'VK_END',
    'PageUp': 'VK_PRIOR',
    'PageDown': 'VK_NEXT',
    'ArrowLeft': 'VK_LEFT',
    'ArrowUp': 'VK_UP',
    'ArrowRight': 'VK_RIGHT',
    'ArrowDown': 'VK_DOWN',
    'F1': 'VK_F1',
    'F2': 'VK_F2',
    'F3': 'VK_F3',
    'F4': 'VK_F4',
    'F5': 'VK_F5',
    'F6': 'VK_F6',
    'F7': 'VK_F7',
    'F8': 'VK_F8',
    'F9': 'VK_F9',
    'F10': 'VK_F10',
    'F11': 'VK_F11',
    'F12': 'VK_F12',
    'Shift': 'VK_LSHIFT',
    //''  : 'VK_RSHIFT',
    'Control': 'VK_LCONTROL',
    //???''  : 'VK_LWIN',
    'Meta': 'VK_RWIN',
    //'': 'VK_LMENU',
    'ScrollLock': 'VK_SCROLL',
    'NumLock': 'VK_NUMLOCK',
    'CapsLock': 'VK_CAPITAL',
    //''  : 'VK_RCONTROL',
    //'': 'VK_MULTIPLY',
    //'': 'VK_ADD',
    //'': 'VK_SUBTRACT',
    //'': 'VK_DIVIDE',
    'PrintScreen': 'VK_SNAPSHOT', //not sure abt this!
    'ContextMenu': 'VK_RMENU',
    'c' : '46',
    'v' : '47',
}

async function sendRDPMousePos(canvas, evt) {
    // this must refer to a canvas!!!!
    var client_id = canvas.getAttribute("canvasclientid");
    var rect = canvas.getBoundingClientRect();
    var x = evt.clientX - rect.left;
    var y = evt.clientY - rect.top;
    var press = false;
    var release = false;
    var button = 0;
    if (evt.type == "mousemove") {
        press = false;
        release = false;
        button = 0;
    } else {
        if (evt.button in mouse_to_rdp) {
            button = mouse_to_rdp[evt.button];
        }
        if (evt.type == "mousedown") {
            press = true;
        }
        if (evt.type == "mouseup") {
            release = true;
        }
    }


    await rdp_events[client_id]['mouse'](x, y, button, press, release);

}

function sendRDPKeys(canvas, evt) {
    // this must refer to a canvas!!!!
    // evt, client_id, press = false, release = false) {
    // canvasclientid

    // this is buggy :( 
    // you can send either one unicode char or one integer corresponding to a scancode
    var client_id = canvas.getAttribute("canvasclientid");
    var press = false;
    if (evt.type == "keydown") {
        press = true;
    }
    var is_scancode = false;
    var keycode = null;
    if (evt.key.length == 1 && evt.key != 'c' && evt.key != 'v') {
        is_scancode = false;
        keycode = evt.key;
    } else {
        if (evt.key in rdp_specialchar_to_name) {
            keycode = rdp_specialchar_to_name[evt.key];
            is_scancode = true;
        } else {
            console.log("Not recognized key: " + evt.key);
        }
    }
    rdp_events[client_id]['keyboard'](keycode, press, is_scancode);
}

function addNewRDPCanvasWindow(cid, cliname, width, height, mouse_cb, keyboard_cb, paste_cb) {
    cid = cid.toString();
    rdp_events[cid] = {};
    rdp_events[cid]['mouse'] = mouse_cb;
    rdp_events[cid]['keyboard'] = keyboard_cb;
    rdp_events[cid]['clipboard'] = mouse_cb;

    var newItemConfig = {
        title: cliname,
        type: 'component',
        componentName: 'rdpWindowComponent',
        componentState: {
            text: 'text',
            clientid: cid,
            rdpwidth: width,
            rdpheight: height,
        }
    };
    myLayout.root.contentItems[0].addChild(newItemConfig);
}

function updateRDPCanvas(cid, imgDataBuffProxy, x, y, width, height) {
    //console.log("Update!");
    //console.log(imgDataBuffProxy);
    try {
        let canvas = document.getElementById(`rdpcanvas-${cid}`);
        let ctx = canvas.getContext("2d");
        let imgDataBuff = imgDataBuffProxy.getBuffer('u8clamped');
        imgDataBuffProxy.destroy();
        imageData = new ImageData(width, height);
        imageData.data.set(imgDataBuff.data);
        ctx.putImageData(imageData, x, y);
        imgDataBuff.release();
    } catch (error) {
        console.error(error);
        return false;
    }
}