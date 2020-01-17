var keyStrokes = [];
var dullard = [40, 38, 37, 37, 65, 39, 40]   //DULLARD code



let base_lastTime = 0;

function update(time = 0) {
    const deltaTime = time - base_lastTime;
    base_lastTime = time;
    
    requestAnimationFrame(update);
    dullard_check(keyStrokes);
}


function equalArray(a, b) {
    if (a === b) return true;
    if (a === null || b === null) return false;
    if (a.length != b.length) return false;

    for (var i = 0; i < a.length; i++) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

function dullard_check(keyStrokes) {
    if (keyStrokes.length >= 7) {
        strokes = keyStrokes.slice(-7)
        if (equalArray(strokes, dullard)) {
            window.alert('DULLARD code detected!');
            console.log('Clearing keystroke array...')
            keyStrokes.length = 0;
            console.log('Sending to Tetri! Enjoy!')
            window.location.href = 'games/tetris';
        }
        
    }
}

document.addEventListener('keydown', event => {
    
    console.log(event);
    keyStrokes.push(event.keyCode)
})

update();