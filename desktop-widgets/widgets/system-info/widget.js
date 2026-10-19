// CPU, memory, disk, temperature, battery, the network and Bluetooth (backend.py).
import {ding, el, log, onEvent, registerFake, request} from './api.js';

const HISTORY_LENGTH = 60;
const cpuHistory = [];
const $ = id => document.getElementById(id);

function formatBytes(bytes, digits = 1) {
    const units = ['B', 'K', 'M', 'G', 'T'];
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit++;
    }
    return `${value.toFixed(unit === 0 ? 0 : digits)}${units[unit]}`;
}

function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return days > 0 ? `up ${days}d ${hours}h` : `up ${hours}h ${minutes}m`;
}

// "10.4 / 15G": the total in the muted color, so the used amount reads first.
function setMeter(id, fraction, used, of = '', level = null) {
    const meter = $(id);
    const fill = meter.querySelector('.bar > i');
    fill.style.width = `${Math.round(Math.min(1, Math.max(0, fraction)) * 100)}%`;
    if (level !== null)
        fill.className = level;
    const value = meter.querySelector('.value');
    value.replaceChildren(used);
    if (of)
        value.append(el('span', 'of', ` / ${of}`));
}

function tempLevel(celsius) {
    if (celsius >= 85)
        return 'crit';
    if (celsius >= 70)
        return 'warn';
    return 'ok';
}

function batteryLevel(percent, charging) {
    if (charging || percent > 20)
        return 'ok';
    return percent > 10 ? 'warn' : 'crit';
}

// The temp bar uses the btop temperature ramp instead of the semantic levels.
const TEMP_COLORS = {ok: 'var(--temp-start)', warn: 'var(--temp-mid)', crit: 'var(--temp-end)'};

function drawCpuGraph() {
    const step = 100 / (HISTORY_LENGTH - 1);
    const offset = HISTORY_LENGTH - cpuHistory.length;
    const points = cpuHistory.map((v, i) => `${((offset + i) * step).toFixed(2)},${(40 - v * 37).toFixed(2)}`);
    $('cpu-line').setAttribute('points', points.join(' '));
    $('cpu-area').setAttribute('d', `M${(offset * step).toFixed(2)},40 L${points.join(' L')} L100,40 Z`);
}

function render(s) {
    $('uptime').textContent = formatUptime(s.uptime);
    $('uptime').title = `${s.host}\n${s.os} · ${s.kernel}`;

    $('cpu-value').textContent = Math.round(s.cpu * 100);
    // While the machine has been busy or hot for a while, name what's using the CPU instead.
    const hog = s.hogs?.[0];
    if (hog) {
        $('cpu-meta').replaceChildren(el('span', 'hog', hog.name), ` · ${hog.cpu}% · load ${s.load.toFixed(2)}`);
        $('cpu-meta').title = s.hogs.map(h => `${h.name}  ${h.cpu}%${h.processes > 1 ? ` (${h.processes} processes)` : ''}`)
            .join('\n') + `\n100% = one of ${s.cores} cores`;
    } else {
        $('cpu-meta').textContent = `CPU${s.freqGhz ? ` · ${s.freqGhz.toFixed(1)} GHz` : ''} · load ${s.load.toFixed(2)}`;
        $('cpu-meta').title = `${s.cores} cores`;
    }
    // The first reply carries the backend's history; later events add one sample each.
    if (s.cpuHistory)
        cpuHistory.splice(0, cpuHistory.length, ...s.cpuHistory.slice(-HISTORY_LENGTH));
    else
        cpuHistory.push(s.cpu);
    if (cpuHistory.length > HISTORY_LENGTH)
        cpuHistory.shift();
    drawCpuGraph();

    setMeter('ram', s.memUsed / s.memTotal, formatBytes(s.memUsed).replace(/G$/, ''), formatBytes(s.memTotal, 0));
    setMeter('disk', s.diskUsed / s.diskTotal, formatBytes(s.diskUsed, 0).replace(/G$/, ''), formatBytes(s.diskTotal, 0));

    $('temp').hidden = s.tempC === null;
    if (s.tempC !== null) {
        const level = tempLevel(s.tempC);
        setMeter('temp', s.tempC / 100, `${Math.round(s.tempC)}°C`, '', level);
        $('temp').querySelector('.bar > i').style.color = TEMP_COLORS[level];
    }

    $('battery').hidden = !s.battery;
    if (s.battery) {
        const {percent, status} = s.battery;
        const charging = status === 'Charging' || status === 'Full';
        setMeter('battery', percent / 100, `${charging ? '⚡ ' : ''}${percent}%`, '', batteryLevel(percent, charging));
    }

    $('down').textContent = `${formatBytes(s.netDown)}/s`;
    $('up').textContent = `${formatBytes(s.netUp)}/s`;
    if (s.network)
        renderNetwork(s.network);
    renderBluetooth(s.bluetooth);
}

// Round trips under 100 ms feel instant; past 250 ms calls and SSH start to drag.
function pingState({link, connectivity, ping}) {
    if (!link)
        return ['crit', 'Offline'];
    if (connectivity === 'portal')
        return ['warn', 'Sign in to network'];
    if (connectivity === 'none' || connectivity === 'limited' || (ping?.samples && ping.ms === null))
        return ['crit', 'No internet'];
    if (!ping?.samples)
        return ['', '…'];
    const level = ping.loss >= 0.25 || ping.ms >= 250 ? 'crit'
        : ping.loss > 0 || ping.ms >= 100 ? 'warn' : 'ok';
    const loss = ping.loss > 0 ? ` · ${Math.round(ping.loss * 100)}% loss` : '';
    return [level, `${ping.ms} ms${loss}`];
}

function linkSpeed(mbps) {
    if (!mbps)
        return '';
    return mbps >= 1000 ? `${mbps / 1000} Gb/s` : `${mbps} Mb/s`;
}

function renderNetwork(net) {
    const {link, vpn, tailscale, ping} = net;
    document.querySelector('.net').classList.toggle('offline', !link);

    const wired = link?.kind === 'ethernet';
    // SVG elements have no .hidden property, so toggle the attribute itself.
    $('wifi-icon').toggleAttribute('hidden', wired);
    $('ethernet-icon').toggleAttribute('hidden', !wired);
    const bars = !link ? 0 : link.signal === null || link.signal >= 67 ? 4 : link.signal >= 34 ? 3 : 2;
    for (let i = 0; i < 4; i++)
        $('wifi-icon').querySelector(`.a${i}`).classList.toggle('on', i < bars);

    $('net-name').textContent = link?.name ?? 'Not connected';
    $('net-detail').textContent = !link ? '' : wired ? linkSpeed(link.speedMbps) : link.band ?? '';
    $('net-link').title = link
        ? `${link.device}${link.signal !== null && !wired ? ` · signal ${link.signal}%` : ''}\nOpen network settings`
        : 'Open network settings';

    const [level, text] = pingState(net);
    $('ping').className = `ping mono ${level}`;
    $('ping-text').textContent = text;
    $('ping').title = ping?.samples
        ? `Ping to ${ping.host}, median of the last few; loss over the last ${ping.samples * 5}s`
        : '';

    const tunnels = (vpn ?? []).map(name => el('span', 'on', name));
    if (tailscale) {
        if (!tailscale.running) {
            tunnels.push(el('span', 'off', 'tailscale off'));
        } else if (tailscale.exitNode) {
            const chip = el('span', 'via', `via ${tailscale.exitNode}`);
            chip.title = 'Traffic goes out through this Tailscale exit node';
            tunnels.push(chip);
        } else {
            const chip = el('span', '', `tailscale ${tailscale.online}/${tailscale.peers}`);
            chip.title = `${tailscale.online} of ${tailscale.peers} devices online`;
            tunnels.push(chip);
        }
    }
    $('tunnels').replaceChildren(...tunnels);
}

// The card has room for three rows; more paired devices than that are left out.
const BT_ROWS = 3;

const BT_ICONS = {
    headset: '<path d="M3 10V8a5 5 0 0 1 10 0v2"/><path d="M3 10h2v3.5H3.8a.8.8 0 0 1-.8-.8zM13 10h-2v3.5h1.2a.8.8 0 0 0 .8-.8z"/>',
    mouse: '<rect x="4.5" y="2" width="7" height="12" rx="3.5"/><path d="M8 4.5v2"/>',
    keyboard: '<rect x="1.5" y="4" width="13" height="8" rx="1.5"/><path d="M4.5 7h0M7 7h0M9.5 7h0M12 7h0M5 9.5h6"/>',
    phone: '<rect x="4.5" y="1.5" width="7" height="13" rx="1.5"/><path d="M7 12h2"/>',
    computer: '<rect x="2" y="3" width="12" height="8" rx="1"/><path d="M6 14h4M8 11v3"/>',
    bluetooth: '<path d="M4.5 5 11.5 11 8 14V2l3.5 3-7 6"/>',
};

function btIcon(icon) {
    const kind = /^audio-(headset|headphones|card)/.test(icon ?? '') ? 'headset'
        : /^input-(mouse|tablet)/.test(icon ?? '') ? 'mouse'
        : icon === 'input-keyboard' ? 'keyboard'
        : icon === 'phone' ? 'phone'
        : icon === 'computer' ? 'computer' : 'bluetooth';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 16 16');
    svg.setAttribute('class', 'net-icon');
    svg.innerHTML = BT_ICONS[kind];
    return svg;
}

function btRow(icon, name, detail) {
    const row = el('button', 'bt-row');
    row.title = 'Bluetooth settings';
    row.append(btIcon(icon), el('span', 'bt-name', name));
    if (detail)
        row.append(el('span', 'muted bt-detail', detail));
    return row;
}

function renderBluetooth(bt) {
    $('bt').hidden = !bt;
    if (!bt)
        return;
    let rows;
    if (!bt.powered) {
        rows = [btRow('bluetooth', 'Bluetooth off')];
        rows[0].classList.add('off');
    } else if (!bt.devices.length) {
        rows = [btRow('bluetooth', 'No paired devices')];
        rows[0].classList.add('off');
    } else {
        rows = bt.devices.slice(0, BT_ROWS).map(d => {
            const row = btRow(d.icon, d.name, d.connected ? d.profile : 'not connected');
            row.classList.toggle('off', !d.connected);
            if (d.profile?.startsWith('HFP'))
                row.querySelector('.bt-detail').title = 'Hands-free mode: the mic is on, so playback quality is lower';
            if (d.connected && d.battery !== null) {
                const level = batteryLevel(d.battery, false);
                const battery = el('span', `bt-battery mono ${level === 'ok' ? '' : level}`);
                const pill = el('i', 'pill');
                const fill = el('b');
                fill.style.width = `${d.battery}%`;
                pill.append(fill);
                battery.append(pill, `${d.battery}%`);
                row.append(battery);
            }
            return row;
        });
    }
    $('bt').replaceChildren(...rows);
}

let fakeCpu = 0.25;
function fakeStats() {
    fakeCpu = Math.min(0.95, Math.max(0.03, fakeCpu + (Math.random() - 0.5) * 0.18));
    return {
        host: 'chimera-Latitude-3520',
        os: 'Ubuntu 26.04.1 LTS',
        kernel: '7.0.0-38-generic',
        uptime: 2 * 86400 + 3 * 3600,
        cpu: fakeCpu,
        cores: 8,
        freqGhz: 2.4 + Math.random(),
        memUsed: 8.1e9 + Math.random() * 3e8,
        memTotal: 15.96e9,
        diskUsed: 134e9,
        diskTotal: 234e9,
        tempC: 48 + fakeCpu * 30,
        hogs: fakeCpu > 0.6 ? [{name: 'chrome', cpu: Math.round(fakeCpu * 400), processes: 23}] : null,
        battery: {percent: 91, status: 'Discharging'},
        netDown: 180e3 + Math.random() * 1.5e6,
        netUp: 12e3 + Math.random() * 80e3,
        load: 0.6 + fakeCpu * 2,
        network: {
            link: {kind: 'wifi', name: 'iQOO Neo9 Pro', device: 'wlp0s20f3', signal: 87, band: '2.4 GHz'},
            vpn: [],
            tailscale: {running: true, online: 2, peers: 2, exitNode: null},
            connectivity: 'full',
            ping: {host: '1.1.1.1', ms: Math.round(30 + fakeCpu * 40), loss: 0, samples: 12},
        },
        bluetooth: {
            powered: true,
            devices: [
                {name: 'Arcticfox-BTM', icon: 'input-mouse', connected: true, battery: 73, profile: null},
                {name: 'realme Buds T310', icon: 'audio-headset', connected: true, battery: 100, profile: 'HFP · mSBC'},
                {name: 'iQOO Neo9 Pro', icon: 'phone', connected: false, battery: null, profile: null},
            ],
        },
    };
}

registerFake(method => {
    if (method !== 'getStats')
        return null;
    return {...fakeStats(), cpuHistory: Array.from({length: HISTORY_LENGTH - 1}, () => fakeStats().cpu)};
});

export function start() {
    $('net-link').addEventListener('click', () => {
        request('openNetworkSettings').catch(e => log(`openNetworkSettings failed: ${e?.message ?? e}`));
    });
    $('bt').addEventListener('click', event => {
        if (event.target.closest('.bt-row'))
            request('openBluetoothSettings').catch(e => log(`openBluetoothSettings failed: ${e?.message ?? e}`));
    });
    onEvent('stats', render);
    request('getStats')
        .then(render)
        .catch(e => log(`getStats failed: ${e?.message ?? e}`));
    if (!ding)
        setInterval(() => render(fakeStats()), 2000);
}

start();
