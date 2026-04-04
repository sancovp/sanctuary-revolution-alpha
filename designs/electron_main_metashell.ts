import { app, BrowserWindow, ipcMain } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import path from 'node:path'
import fs from 'node:fs'
import http from 'node:http'

// Check if a port is already responding with a healthy HTTP service
function isPortHealthy(port: number, path: string = '/'): Promise<boolean> {
    return new Promise((resolve) => {
        const req = http.get({ hostname: 'localhost', port, path, timeout: 2000 }, (res) => {
            resolve(res.statusCode !== undefined && res.statusCode < 500)
        })
        req.on('error', () => resolve(false))
        req.on('timeout', () => { req.destroy(); resolve(false) })
    })
}

// Wait for a port to become healthy, polling every interval ms
function waitForPort(port: number, maxWaitMs: number = 10000, intervalMs: number = 500): Promise<boolean> {
    return new Promise((resolve) => {
        const start = Date.now()
        const check = async () => {
            if (await isPortHealthy(port)) {
                resolve(true)
                return
            }
            if (Date.now() - start >= maxWaitMs) {
                resolve(false)
                return
            }
            setTimeout(check, intervalMs)
        }
        check()
    })
}

let mainWindow: BrowserWindow | null = null
let orchestratorProcess: ChildProcess | null = null
let dockerBridgeProcess: ChildProcess | null = null
let viteProcess: ChildProcess | null = null
let orchestratorEnabled = true  // User toggle
let dockerBridgeEnabled = true  // User toggle
let restartCount = 0
let bridgeRestartCount = 0
const MAX_RESTARTS = 10
const RESTART_DELAY = 2000  // 2 seconds
const VITE_PORT = 5173

// Get the backend path - works in both dev and prod
function getBackendPath(): string {
    if (process.env.NODE_ENV === 'development' || process.env.VITE_DEV_SERVER_URL) {
        // In dev, relative to project root
        return path.join(app.getAppPath(), 'backend')
    } else {
        // In prod, packaged with the app
        return path.join(process.resourcesPath, 'backend')
    }
}

// Get bundled executables path (prod only)
function getBundledPath(): string {
    return path.join(process.resourcesPath, 'backend-dist')
}

function isDev(): boolean {
    return process.env.NODE_ENV === 'development' || !!process.env.VITE_DEV_SERVER_URL
}

// Get orchestrator status
function getOrchestratorStatus(): { running: boolean; enabled: boolean; restarts: number; pid: number | null } {
    return {
        running: orchestratorProcess !== null && !orchestratorProcess.killed,
        enabled: orchestratorEnabled,
        restarts: restartCount,
        pid: orchestratorProcess?.pid ?? null,
    }
}

// Notify renderer of status change
function notifyStatusChange(): void {
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('orchestrator-status', getOrchestratorStatus())
    }
}

// Start the orchestrator server
async function startOrchestrator(): Promise<void> {
    if (!orchestratorEnabled) {
        console.log('Orchestrator disabled by user')
        return
    }

    if (orchestratorProcess && !orchestratorProcess.killed) {
        console.log('Orchestrator already running')
        return
    }

    // Check if port 8090 is already occupied by a healthy orchestrator
    const alreadyUp = await isPortHealthy(8090)
    if (alreadyUp) {
        console.log('Orchestrator already responding on port 8090 — adopting existing instance')
        return
    }

    if (isDev()) {
        // In dev, use Python script
        const orchestratorPath = path.join(getBackendPath(), 'orchestrator')
        const serverPath = path.join(orchestratorPath, 'server.py')

        if (!fs.existsSync(serverPath)) {
            console.error(`Orchestrator not found at: ${serverPath}`)
            return
        }

        console.log(`Starting orchestrator (dev) from: ${serverPath} (restart #${restartCount})`)

        const pythonCmd = process.platform === 'darwin'
            ? '/opt/homebrew/bin/python3.11'
            : 'python3'

        orchestratorProcess = spawn(pythonCmd, [serverPath], {
            cwd: orchestratorPath,
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            stdio: ['ignore', 'pipe', 'pipe'],
        })
    } else {
        // In prod, use bundled Python script directly
        // (Same pattern as docker_bridge — avoids stale PyInstaller binaries)
        const orchestratorPath = path.join(getBackendPath(), 'orchestrator')
        const serverPath = path.join(orchestratorPath, 'server.py')

        if (!fs.existsSync(serverPath)) {
            console.error(`Orchestrator Python script not found at: ${serverPath}`)
            return
        }

        console.log(`Starting orchestrator (prod) from: ${serverPath} (restart #${restartCount})`)

        const pythonCmd = process.platform === 'darwin'
            ? '/opt/homebrew/bin/python3.11'
            : 'python3'

        orchestratorProcess = spawn(pythonCmd, [serverPath], {
            cwd: orchestratorPath,
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            stdio: ['ignore', 'pipe', 'pipe'],
        })
    }

    // Log stdout
    orchestratorProcess.stdout?.on('data', (data) => {
        console.log(`[Orchestrator] ${data.toString().trim()}`)
    })

    // Log stderr
    orchestratorProcess.stderr?.on('data', (data) => {
        console.error(`[Orchestrator] ${data.toString().trim()}`)
    })

    // Handle process exit - AUTO RESTART if enabled
    orchestratorProcess.on('exit', (code, signal) => {
        console.log(`Orchestrator exited with code ${code}, signal ${signal}`)
        orchestratorProcess = null
        notifyStatusChange()

        // Auto-restart if enabled and under max restarts
        if (orchestratorEnabled && restartCount < MAX_RESTARTS) {
            restartCount++
            console.log(`Auto-restarting orchestrator in ${RESTART_DELAY}ms (attempt ${restartCount}/${MAX_RESTARTS})...`)
            setTimeout(() => {
                startOrchestrator()
            }, RESTART_DELAY)
        } else if (restartCount >= MAX_RESTARTS) {
            console.error(`Orchestrator crashed ${MAX_RESTARTS} times, giving up. User can restart manually.`)
        }
    })

    orchestratorProcess.on('error', (err) => {
        console.error(`Failed to start orchestrator: ${err.message}`)
        orchestratorProcess = null
        notifyStatusChange()
    })

    // Reset restart count on successful sustained run (30 seconds)
    setTimeout(() => {
        if (orchestratorProcess && !orchestratorProcess.killed) {
            console.log('Orchestrator stable, resetting restart count')
            restartCount = 0
        }
    }, 30000)

    notifyStatusChange()
}

// Stop the orchestrator gracefully
function stopOrchestrator(): void {
    if (orchestratorProcess) {
        console.log('Stopping orchestrator...')
        orchestratorProcess.kill('SIGTERM')

        // Force kill after 5 seconds if still running
        setTimeout(() => {
            if (orchestratorProcess) {
                console.log('Force killing orchestrator...')
                orchestratorProcess.kill('SIGKILL')
                orchestratorProcess = null
                notifyStatusChange()
            }
        }, 5000)
    }
}

// Start the Docker Bridge server
async function startDockerBridge(): Promise<void> {
    if (!dockerBridgeEnabled) {
        console.log('Docker Bridge disabled by user')
        return
    }

    if (dockerBridgeProcess && !dockerBridgeProcess.killed) {
        console.log('Docker Bridge already running')
        return
    }

    // Check if port 5051 is already occupied by a healthy backend
    const alreadyUp = await isPortHealthy(5051)
    if (alreadyUp) {
        console.log('Docker Bridge already responding on port 5051 — adopting existing instance')
        return
    }

    // --- Handler setup (defined first, called after spawn) ---
    function setupDockerBridgeHandlers() {
        if (!dockerBridgeProcess) return

        // Log stdout
        dockerBridgeProcess.stdout?.on('data', (data) => {
            console.log(`[DockerBridge] ${data.toString().trim()}`)
        })

        // Log stderr
        dockerBridgeProcess.stderr?.on('data', (data) => {
            console.error(`[DockerBridge] ${data.toString().trim()}`)
        })

        // Handle process exit - AUTO RESTART if enabled
        dockerBridgeProcess.on('exit', (code, signal) => {
            console.log(`Docker Bridge exited with code ${code}, signal ${signal}`)
            dockerBridgeProcess = null

            // Auto-restart if enabled and under max restarts
            if (dockerBridgeEnabled && bridgeRestartCount < MAX_RESTARTS) {
                bridgeRestartCount++
                console.log(`Auto-restarting Docker Bridge in ${RESTART_DELAY}ms (attempt ${bridgeRestartCount}/${MAX_RESTARTS})...`)
                setTimeout(() => {
                    startDockerBridge()
                }, RESTART_DELAY)
            } else if (bridgeRestartCount >= MAX_RESTARTS) {
                console.error(`Docker Bridge crashed ${MAX_RESTARTS} times, giving up.`)
            }
        })

        dockerBridgeProcess.on('error', (err) => {
            console.error(`Failed to start Docker Bridge: ${err.message}`)
            dockerBridgeProcess = null
        })

        // Reset restart count on successful sustained run (30 seconds)
        setTimeout(() => {
            if (dockerBridgeProcess && !dockerBridgeProcess.killed) {
                console.log('Docker Bridge stable, resetting restart count')
                bridgeRestartCount = 0
            }
        }, 30000)
    }

    // --- Spawn the process ---
    if (isDev()) {
        // In dev, use Python script
        const backendPath = getBackendPath()
        const bridgePath = path.join(backendPath, 'docker_bridge.py')

        if (!fs.existsSync(bridgePath)) {
            console.error(`Docker Bridge not found at: ${bridgePath}`)
            return
        }

        console.log(`Starting Docker Bridge (dev) from: ${bridgePath} (restart #${bridgeRestartCount})`)

        const pythonCmd = process.platform === 'darwin'
            ? '/opt/homebrew/bin/python3.11'
            : 'python3'

        dockerBridgeProcess = spawn(pythonCmd, [bridgePath], {
            cwd: backendPath,
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            stdio: ['ignore', 'pipe', 'pipe'],
        })
    } else {
        // In prod, use bundled Python script directly
        // NOTE: The PyInstaller binary (backend-dist/docker_bridge) is stale and binds
        // to wrong port (5100 instead of 5051). Using Python script until binary is recompiled.
        const scriptPath = path.join(getBackendPath(), 'docker_bridge.py')
        const cwd = getBackendPath()

        if (!fs.existsSync(scriptPath)) {
            console.error(`Docker Bridge Python script not found at: ${scriptPath}`)
            return
        }

        console.log(`Starting Docker Bridge (prod) from: ${scriptPath} (restart #${bridgeRestartCount})`)
        const pythonCmd = process.platform === 'darwin'
            ? '/opt/homebrew/bin/python3.11'
            : 'python3'
        dockerBridgeProcess = spawn(pythonCmd, [scriptPath], {
            cwd: cwd,
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            stdio: ['ignore', 'pipe', 'pipe'],
        })
    }

    // Always attach handlers — this covers dev mode and prod binary mode.
    // (Python fallback also calls setupDockerBridgeHandlers internally since
    // it replaces the process reference, but double-attach is harmless on Node.)
    setupDockerBridgeHandlers()
}

// Stop the Docker Bridge gracefully
function stopDockerBridge(): void {
    if (dockerBridgeProcess) {
        console.log('Stopping Docker Bridge...')
        dockerBridgeProcess.kill('SIGTERM')

        setTimeout(() => {
            if (dockerBridgeProcess) {
                console.log('Force killing Docker Bridge...')
                dockerBridgeProcess.kill('SIGKILL')
                dockerBridgeProcess = null
            }
        }, 5000)
    }
}

// ============================================================================
// Vite Dev Server — keeps the inner app hot-reloadable at all times
// Even in "production" mode, we run Vite so agents can edit files and
// the webview updates via HMR. This is the key to the meta-frontend.
// ============================================================================

async function startViteDevServer(): Promise<void> {
    // Check if Vite is already running (e.g. npm run dev started it)
    const alreadyUp = await isPortHealthy(VITE_PORT)
    if (alreadyUp) {
        console.log(`Vite dev server already responding on port ${VITE_PORT} — adopting existing instance`)
        return
    }

    // In dev mode, vite-plugin-electron already manages the Vite server.
    // We only need to spawn our own Vite in prod/packaged mode.
    if (isDev()) {
        console.log('Dev mode: Vite managed by vite-plugin-electron, skipping spawn')
        return
    }

    // For prod hot mode: spawn Vite from bundled app source
    const projectRoot = path.join(process.resourcesPath, 'app-source')

    if (!fs.existsSync(projectRoot)) {
        console.log('No app-source directory found for prod hot mode — falling back to static bundle')
        return
    }

    console.log('Starting Vite dev server for hot frontend...')
    const npxPath = process.platform === 'win32' ? 'npx.cmd' : 'npx'
    viteProcess = spawn(npxPath, ['vite', '--port', String(VITE_PORT), '--host'], {
        cwd: projectRoot,
        env: { ...process.env },
        stdio: ['ignore', 'pipe', 'pipe'],
    })

    viteProcess.stdout?.on('data', (data: Buffer) => {
        console.log(`[Vite] ${data.toString().trim()}`)
    })

    viteProcess.stderr?.on('data', (data: Buffer) => {
        console.log(`[Vite] ${data.toString().trim()}`)
    })

    viteProcess.on('exit', (code) => {
        console.log(`Vite dev server exited with code ${code}`)
        viteProcess = null
    })

    viteProcess.on('error', (err) => {
        console.error(`Failed to start Vite: ${err.message}`)
        viteProcess = null
    })
}

function stopViteDevServer(): void {
    if (viteProcess) {
        console.log('Stopping Vite dev server...')
        viteProcess.kill('SIGTERM')
        setTimeout(() => {
            if (viteProcess) {
                viteProcess.kill('SIGKILL')
                viteProcess = null
            }
        }, 3000)
    }
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        titleBarStyle: 'hiddenInset',
        backgroundColor: '#08060d',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            webviewTag: true,  // Enable <webview> for meta-shell
        },
    })

    // Load the meta-shell which contains a <webview> pointing to the app
    const metaShellPath = isDev()
        ? path.join(app.getAppPath(), 'meta-shell.html')
        : path.join(app.getAppPath(), 'dist', 'meta-shell.html')

    // The app always runs from the Vite dev server for hot-reloading
    const appUrl = `http://localhost:${VITE_PORT}`

    mainWindow.loadFile(metaShellPath).then(() => {
        mainWindow?.webContents.executeJavaScript(
            `document.body.dataset.appUrl = '${appUrl}'; ` +
            `document.getElementById('app-webview').src = '${appUrl}';`
        )
    })

    if (isDev()) {
        mainWindow.webContents.openDevTools({ mode: 'detach' })
    }

    mainWindow.on('closed', () => {
        mainWindow = null
    })

    // Send initial status once window is ready
    mainWindow.webContents.on('did-finish-load', () => {
        notifyStatusChange()
    })
}

// ============================================================================
// IPC Handlers for Frontend Control
// ============================================================================

ipcMain.handle('orchestrator:status', () => {
    return getOrchestratorStatus()
})

ipcMain.handle('orchestrator:start', () => {
    orchestratorEnabled = true
    restartCount = 0
    startOrchestrator()
    return getOrchestratorStatus()
})

ipcMain.handle('orchestrator:stop', () => {
    orchestratorEnabled = false
    stopOrchestrator()
    return getOrchestratorStatus()
})

ipcMain.handle('orchestrator:restart', () => {
    orchestratorEnabled = true
    restartCount = 0
    stopOrchestrator()
    setTimeout(() => {
        startOrchestrator()
    }, 1000)
    return getOrchestratorStatus()
})

// ============================================================================
// App lifecycle
// ============================================================================

// Single-instance lock — prevent multiple windows
const gotTheLock = app.requestSingleInstanceLock()
let isBooting = true

if (!gotTheLock) {
    // Another instance is already running, quit this one
    app.quit()
} else {
    app.on('second-instance', () => {
        // Focus the existing window when a second instance tries to launch
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore()
            mainWindow.focus()
        }
    })

    app.whenReady().then(async () => {
        // Start backend servers
        await startDockerBridge()
        await startOrchestrator()
        await startViteDevServer()

        // Wait for Docker Bridge to be healthy before showing window
        console.log('Waiting for Docker Bridge to become healthy...')
        const bridgeHealthy = await waitForPort(5051, 10000)
        if (bridgeHealthy) {
            console.log('Docker Bridge is healthy!')
        } else {
            console.warn('Docker Bridge did not become healthy within 10s — showing window anyway')
        }

        // Wait for Vite to be ready
        console.log('Waiting for Vite dev server...')
        const viteHealthy = await waitForPort(VITE_PORT, 15000)
        if (viteHealthy) {
            console.log('Vite dev server is ready!')
        } else {
            console.warn('Vite dev server not ready within 15s — showing window anyway')
        }

        createWindow()
        isBooting = false
    })
}

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('activate', () => {
    if (isBooting) return  // Don't create window while still starting up
    if (mainWindow === null) {
        createWindow()
    } else {
        mainWindow.focus()
    }
})

// Clean up on quit
app.on('will-quit', () => {
    orchestratorEnabled = false  // Prevent auto-restart during shutdown
    dockerBridgeEnabled = false
    stopOrchestrator()
    stopDockerBridge()
    stopViteDevServer()
})

// Handle unexpected termination
process.on('SIGINT', () => {
    orchestratorEnabled = false
    dockerBridgeEnabled = false
    stopOrchestrator()
    stopDockerBridge()
    stopViteDevServer()
    app.quit()
})

process.on('SIGTERM', () => {
    orchestratorEnabled = false
    dockerBridgeEnabled = false
    stopOrchestrator()
    stopDockerBridge()
    stopViteDevServer()
    app.quit()
})
