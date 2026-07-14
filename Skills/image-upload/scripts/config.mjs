import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

/**
 * Lightweight .env parser.
 * Searches for and parses a .env file to load environment variables.
 */
export function loadEnv() {
  const envPaths = [
    path.join(process.cwd(), '.env'),
    path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '.env'),
    path.join(os.homedir(), '.claude', '.env'),
    path.join(os.homedir(), '.env'),
  ];

  for (const envPath of envPaths) {
    try {
      if (fs.existsSync(envPath)) {
        const content = fs.readFileSync(envPath, 'utf8');
        for (const line of content.split('\n')) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) continue;
          
          const match = trimmed.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
          if (match) {
            const key = match[1];
            let val = match[2] || '';
            // Remove wrapping quotes if present
            if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
            else if (val.startsWith("'") && val.endsWith("'")) val = val.slice(1, -1);
            process.env[key] = val;
          }
        }
        break; // Stop at the first .env file found
      }
    } catch (e) {
      // Ignore reading errors
    }
  }
}
