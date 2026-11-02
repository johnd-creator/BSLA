import {preciseInstant} from './pdm-history';

const months = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
export const MISSING_WO_VALUE = 'BELUM TERSEDIA';
// Presentation only. Never supply a zone for an unzoned source clock. -00:00
// explicitly means unknown offset and must not be converted to WIB either.
export function woDate(value: string | null | undefined): string {
  if (value == null || value === '') return MISSING_WO_VALUE;
  const naive = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?$/.exec(value);
  const unknownOffset = value.endsWith('-00:00');
  if (naive || unknownOffset) {
    const local = unknownOffset ? value.slice(0,-6) : value;
    if (!preciseInstant(local+'Z')) return 'Format waktu tidak valid';
    const m = /^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})/.exec(local);
    if (!m) return 'Format waktu tidak valid';
    return `${Number(m[3])} ${months[Number(m[2])-1]} ${m[1]}, ${m[4]}.${m[5]} · zona waktu belum diverifikasi`;
  }
  if (!preciseInstant(value)) return 'Format waktu tidak valid';
  const parts = new Intl.DateTimeFormat('id-ID', {timeZone:'Asia/Jakarta',day:'numeric',month:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value));
  const part = (key: Intl.DateTimeFormatPartTypes) => parts.find(p => p.type === key)?.value ?? '';
  return `${part('day')} ${months[Number(part('month'))-1]} ${part('year')}, ${part('hour')}.${part('minute')} WIB`;
}
