const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const net = require('net');

let mainWindow;
let pythonProcess = null;
let PYTHON_PORT = 3002;

// Utility to find an open port
function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, () => {
      const port = server.address().port;
      server.close(() => {
        resolve(port);
      });
    });
  });
}

// Determine path to Python backend
const getPythonBackendPath = () => {
  if (app.isPackaged) {
    // In Production: The binary is in Contents/Resources/app_server/app_server
    return path.join(process.resourcesPath, 'app_server', 'app_server');
  } else {
    // In Development: Using local virtual environment python
    return path.join(__dirname, 'venv', 'bin', 'python3');
  }
};

const getPythonArgs = (port) => {
    if (app.isPackaged) {
        return ['--port', port.toString()];
    } else {
        return ['app.py', '--port', port.toString()];
    }
};

const getPythonCwd = () => {
     if (app.isPackaged) {
         return path.join(process.resourcesPath, 'app_server'); // Run inside the extracted Resources dir
     } else {
         return __dirname; // Run from source directory
     }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    show: false, // Don't show until backend is ready
    title: "EDTech PDF",
    backgroundColor: '#ffffff'
  });

  mainWindow.setMenuBarVisibility(false);
  
  // Wait for the backend to be alive before loading the URL
  waitForBackend(`http://127.0.0.1:${PYTHON_PORT}`, 100, 30) // Wait max 3 seconds
    .then(() => {
        mainWindow.loadURL(`http://127.0.0.1:${PYTHON_PORT}`);
        mainWindow.once('ready-to-show', () => {
            mainWindow.show();
        });
    })
    .catch(err => {
        dialog.showErrorBox(
            'Error Fatal', 
            'No se pudo inicializar el motor de procesamiento (Backend Time-out).'
        );
        app.quit();
    });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Function to ping the backend until it responds
function waitForBackend(url, interval, maxTries) {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const check = () => {
            attempts++;
            http.get(url, (res) => {
                if (res.statusCode === 200 || res.statusCode === 404 || res.statusCode === 302) {
                    resolve();
                } else {
                   retry();
                }
            }).on('error', () => {
                retry();
            });
        };

        const retry = () => {
            if (attempts >= maxTries) {
                 reject(new Error("Timeout waiting for backend"));
            } else {
                 setTimeout(check, interval);
            }
        };
        check();
    });
}

function killPythonProcess() {
  if (pythonProcess) {
    try {
        if (process.platform === 'win32') {
             spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
        } else {
             process.kill(-pythonProcess.pid, 'SIGTERM'); // Kill process group
        }
    } catch (e) {
        console.error('Error killing python process:', e);
    }
    pythonProcess = null;
  }
}

app.whenReady().then(async () => {
  PYTHON_PORT = await getFreePort();
  const backendPath = getPythonBackendPath();
  const backendArgs = getPythonArgs(PYTHON_PORT);
  const cwd = getPythonCwd();
  
  console.log(`[Electron] Arrancando backend: ${backendPath} ${backendArgs.join(' ')} en ${cwd}`);

  // Need detached and new session to kill process tree successfully on Mac/Linux
  try {
      pythonProcess = spawn(backendPath, backendArgs, {
          cwd: cwd,
          detached: process.platform !== 'win32',
          env: process.env // Inherit env
      });

      pythonProcess.stdout.on('data', (data) => console.log(`[Backend]: ${data}`));
      pythonProcess.stderr.on('data', (data) => console.error(`[Backend Error]: ${data}`));
      pythonProcess.on('close', (code) => console.log(`[Backend] Exited with code ${code}`));
  } catch(e) {
      console.error("[Electron] Falla al iniciar python process:", e);
      dialog.showErrorBox("Error de Inicio", "No se pudo iniciar el servicio en el background. Comprueba tu antivirus.");
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  killPythonProcess();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  killPythonProcess();
});
