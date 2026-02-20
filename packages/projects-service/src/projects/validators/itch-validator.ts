import axios from 'axios';
import * as cheerio from 'cheerio';

const ITCH_URL_PATTERN =
  /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/i;

export function isItchUrl(url: string): boolean {
  return ITCH_URL_PATTERN.test(url);
}

export async function isPlayable(
  url: string,
  timeout = 10000,
): Promise<boolean> {
  try {
    const response = await axios.get(url, {
      timeout,
      maxRedirects: 5,
    });
    const $ = cheerio.load(response.data);
    return $('.game_frame').length > 0;
  } catch {
    return false;
  }
}
