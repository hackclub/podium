// Turns the GitHub and itch.io checks on submit off (or back on with ON=1) so
// the load test never sends traffic to github.com / itch.io.
import { check } from 'k6';
import { ADMIN_EMAIL, api } from './lib.js';

export const options = { iterations: 1, vus: 1 };

export default function () {
  const on = __ENV.ON === '1';
  const res = api('PUT', '/events/admin/platform-settings', ADMIN_EMAIL, 'PUT platform-settings', {
    github_validation_enabled: on,
    itch_validation_enabled: on,
  });
  check(res, { 'settings saved': (r) => r.status === 200 });
  console.log(res.status, res.body);
}
