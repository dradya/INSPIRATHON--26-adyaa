import { copyFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const envPath = resolve(process.cwd(), '.env')
const examplePath = resolve(process.cwd(), '.env.example')

if (existsSync(envPath)) {
  console.log('.env already exists; leaving it unchanged.')
} else {
  copyFileSync(examplePath, envPath)
  console.log('Created .env from .env.example.')
  console.log('Add your Supabase project URL and anon/public key to .env before starting the app.')
}
