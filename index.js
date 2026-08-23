/**
 * AlgoFight Linux Standalone Service Node Launcher
 */
const { spawn } = require('child_process');
const path = require('path');

console.log('Launching AlgoFight Linux Python Service...');

const pythonBin = process.env.PYTHON_BIN || '/home/arin/myenv/bin/python';
const runnerScript = path.join(__dirname, 'run_server.py');

const child = spawn(pythonBin, [runnerScript], {
  stdio: 'inherit',
  env: process.env,
});

child.on('error', (err) => {
  console.error('Failed to start python process:', err);
});

child.on('exit', (code, signal) => {
  console.log(`Process exited with code ${code} and signal ${signal}`);
});
