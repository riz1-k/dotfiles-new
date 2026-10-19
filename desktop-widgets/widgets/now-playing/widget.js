import {connect, ding} from './host.js';

const $ = id => document.getElementById(id);

let state = null;

function formatTime(us) {
    const total = Math.max(0, Math.floor(us / 1e6));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor(total / 60) % 60;
    const seconds = String(total % 60).padStart(2, '0');
    return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${seconds}` : `${minutes}:${seconds}`;
}

// The backend only sends the position when it changes unexpectedly; in between
// it's extrapolated from when it was read.
function currentPosition(p) {
    let position = p.positionUs;
    if (p.status === 'Playing')
        position += (Date.now() - p.positionAt) * 1000 * (p.rate || 1);
    return p.lengthUs ? Math.min(position, p.lengthUs) : position;
}

function renderProgress() {
    const p = state?.player;
    if (!p)
        return;
    const hasLength = p.lengthUs > 0;
    const position = currentPosition(p);
    $('progress').hidden = !hasLength;
    $('fill').style.width = hasLength ? `${(position / p.lengthUs) * 100}%` : '0';
    $('time').textContent = hasLength ? `${formatTime(position)} / ${formatTime(p.lengthUs)}` : '';
}

function setArt(src) {
    const img = $('art');
    if (!src) {
        img.hidden = true;
        img.removeAttribute('src');
    } else if (img.getAttribute('src') !== src) {
        img.src = src;
        img.hidden = false;
    }
}

function render(s) {
    state = s;
    const p = s.player;
    const idle = !p || (!p.title && p.status === 'Stopped');
    document.body.classList.toggle('idle', idle);
    if (idle)
        return;

    document.body.classList.toggle('playing', p.status === 'Playing');
    $('source').textContent = p.name;
    $('switch').hidden = s.playerCount < 2;
    $('title').textContent = p.title || 'Unknown title';
    $('title').title = p.title;
    $('artist').textContent = [p.artist, p.album].filter(Boolean).join(' — ');
    $('play-pause').disabled = !p.canPlayPause;
    $('previous').disabled = !p.canGoPrevious;
    $('next').disabled = !p.canGoNext;
    setArt(p.art);
    renderProgress();
}

function control(method) {
    if (ding) {
        ding.backendRequest(method)
            .then(render)
            .catch(e => ding.log(`${method} failed: ${e?.message ?? e}`));
        return;
    }
    // Preview: only play/pause does anything.
    const p = state?.player;
    if (method === 'playPause' && p) {
        p.positionUs = currentPosition(p);
        p.positionAt = Date.now();
        p.status = p.status === 'Playing' ? 'Paused' : 'Playing';
        render(state);
    }
}

$('play-pause').addEventListener('click', () => control('playPause'));
$('previous').addEventListener('click', () => control('previous'));
$('next').addEventListener('click', () => control('next'));
$('switch').addEventListener('click', () => control('switchPlayer'));
setInterval(renderProgress, 1000);

const fakeState = {
    playerCount: 2,
    player: {
        id: 'org.mpris.MediaPlayer2.spotify', name: 'Spotify', status: 'Playing',
        title: 'Midnight City', artist: 'M83', album: "Hurry Up, We're Dreaming",
        art: '../../preview/cover.jpg', lengthUs: 243e6, positionUs: 61e6, positionAt: Date.now(), rate: 1,
        canPlayPause: true, canGoPrevious: true, canGoNext: true,
    },
};

function fake() {
    return new URLSearchParams(location.search).has('idle') ? {player: null, playerCount: 0} : fakeState;
}

connect({event: 'state', request: 'getState', render, fake, fakeIntervalMs: 60 * 60 * 1000});
