// Prints a one-line shell command that runs a SQL file against the loadtest
// database from inside an app pod (database pods can't be exec'd into, and the
// loadtest database is not exposed publicly). Paste the output into
// `orchard exec` / exec_in_pod on the loadtest podium-events deployment.
//
//   node loadtest/run-sql.mjs loadtest/schema.sql
import { readFileSync } from 'node:fs';

const file = process.argv[2];
if (!file) {
  console.error('usage: node loadtest/run-sql.mjs <file.sql>');
  process.exit(1);
}
const sql = Buffer.from(readFileSync(file, 'utf8')).toString('base64');
const js = [
  "const {Client}=require('/app/node_modules/.pnpm/pg@8.18.0/node_modules/pg');",
  '(async()=>{',
  'const c=new Client({connectionString:process.env.PODIUM_DATABASE_URL_RW});',
  'await c.connect();',
  `const r=await c.query(Buffer.from('${sql}','base64').toString());`,
  'for(const x of [].concat(r)){if(x.rows&&x.rows.length)console.log(JSON.stringify(x.rows))}',
  "console.log('ok');await c.end()",
  '})().catch(e=>{console.error(e.message);process.exit(1)})',
].join('');
console.log(`cd /app && node -e "${js}"`);
