#!/usr/bin/env node
/**
* Vercel CLI Login Authorization Script (Cross-Platform)
*/
const { spawnSync, spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const isWindows = os.platform() === 'win32';

function createSecureLogFile() {
const tmpDir = path.join(process.cwd(), '.vercel-tmp');
if (!fs.existsSync(tmpDir)) {
fs.mkdirSync(tmpDir, { recursive: true });
}
if (!isWindows) {
try { fs.chmodSync(tmpDir, 0o700); } catch (e) { /* best effort */ }
}
return path.join(tmpDir, 'login.log');
}

const LOG_FILE = createSecureLogFile();
const ALLOWED_COMMANDS = new Set(['vercel']);

function log(msg) { console.error(msg); }

function commandExists(cmd) {
if (!ALLOWED_COMMANDS.has(cmd)) throw new Error(`Command not in whitelist: ${cmd}`);
try {
if (isWindows) {
const result = spawnSync('where', [cmd], { stdio: 'ignore' });
return result.status === 0;
} else {
const result = spawnSync('sh', ['-c', `command -v "$1"`, '--', cmd], { stdio: 'ignore' });
return result.status === 0;
}
} catch { return false; }
}

function getCommandOutput(cmd, args) {
try {
const result = spawnSync(cmd, args, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'], shell: isWindows });
return result.status === 0 ? (result.stdout || '').trim() : null;
} catch { return null; }
}

function checkVercelInstalled() {
if (!commandExists('vercel')) {
log('Error: Vercel CLI is not installed');
process.exit(1);
}
}

function checkLoginStatus() {
log('Checking login status...');
try {
const result = spawnSync('vercel', ['whoami'], { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], shell: isWindows });
const output = (result.stdout || '').trim();
if (result.status === 0 && output && !output.includes('Error') && !output.includes('not logged in')) {
log(`Logged in as: ${output}`);
return true;
}
} catch { }
return false;
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

function startBackgroundLogin() {
const logStream = fs.openSync(LOG_FILE, 'w');
const child = spawn('vercel', ['login'], {
detached: true,
stdio: ['ignore', logStream, logStream],
shell: isWindows
});
child.unref();
log(`Background login process started (PID: ${child.pid})`);
const pidFile = LOG_FILE + '.pid';
fs.writeFileSync(pidFile, String(child.pid));
return child.pid;
}

function openBrowser(url) {
const urlPattern = /^https:\/\/vercel\.com\/oauth\/device\?user_code=[A-Z0-9-]+$/;
if (!urlPattern.test(url)) {
log(`URL does not match expected pattern, opening anyway: ${url}`);
}
const platform = os.platform();
try {
if (platform === 'darwin') {
spawnSync('open', [url], { stdio: 'ignore' });
} else if (platform === 'win32') {
spawnSync('powershell', ['-Command', `Start-Process '${url}'`], { stdio: 'ignore', windowsHide: true });
} else {
spawnSync('xdg-open', [url], { stdio: 'ignore' });
}
log('Browser opened automatically');
} catch (error) {
log(`Failed to open browser: ${error.message}`);
}
}

async function waitForAuthUrl() {
for (let i = 0; i < 40; i++) {
await sleep(500);
try {
if (fs.existsSync(LOG_FILE)) {
const content = fs.readFileSync(LOG_FILE, 'utf8');
const match = content.match(/https:\/\/vercel\.com\/oauth\/device\?user_code=[A-Z0-9-]+(?=\s|$)/);
if (match) return match[0];
}
} catch (e) {
if (e.code !== 'ENOENT') log(`Warning: ${e.code || e.message}`);
}
}
return null;
}

async function doLogin() {
log('Starting login authorization...');
const loginPid = startBackgroundLogin();
log('Waiting for authorization URL...');
const authUrl = await waitForAuthUrl();
if (authUrl) {
log('Authorization URL extracted');
openBrowser(authUrl);
console.log(JSON.stringify({ status: 'needs_auth', auth_url: authUrl, log_file: LOG_FILE }));
} else {
log('Failed to get authorization URL');
process.exit(1);
}
}

async function main() {
checkVercelInstalled();
if (checkLoginStatus()) {
log('Already logged in, no need to login again.');
console.log(JSON.stringify({ status: 'already_logged_in', message: 'Already logged in' }));
process.exit(0);
}
await doLogin();
}
main();
