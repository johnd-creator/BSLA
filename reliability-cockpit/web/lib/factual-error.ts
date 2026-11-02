import {ApiError} from './api';

/** Presentation only: no backend body, account identity, or policy change. */
export function factualErrorMessage(error:unknown):string {
  if(error instanceof ApiError&&error.status===403)return 'Akses data faktual memerlukan capability atau scope yang disetujui. Akun ini belum memiliki akses ke ringkasan portfolio.';
  if(error instanceof ApiError&&error.status===401)return 'Sesi berakhir. Silakan masuk kembali.';
  if(error instanceof ApiError&&error.status>=400&&error.status<500)return 'Permintaan data faktual tidak dapat diproses.';
  return 'Layanan data faktual belum tersedia. Coba lagi; kegagalan ini tidak menyatakan data kosong.';
}

export type FactualErrorKind = 'access' | 'session' | 'service' | 'request';
export function factualErrorKind(error:unknown):FactualErrorKind {
 if(error instanceof ApiError){if(error.status===403)return 'access';if(error.status===401)return 'session';if(error.status>=400&&error.status<500)return 'request';}
 return 'service';
}
