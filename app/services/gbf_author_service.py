"""
GBF Hazırlayıcı Sertifika Servisi
===================================
KKDİK gereği bir GBF'nin yasal geçerliliği için
hazırlayıcının sertifika bilgisi zorunludur.

Sertifika veren kurumlar (TÜRKAK akreditasyonlu):
  - TÜRKAK onaylı belgelendirme kuruluşları
  - Türkiye Kimya Sanayicileri Derneği (TKSD)
  - İlgili meslek odaları

PDF Bölüm 16'ya eklenir.
"""

from datetime import date, datetime
from typing import Optional


def validate_certificate(cert_data: dict) -> dict:
    """
    Sertifika bilgilerini doğrula.
    
    cert_data = {
        'name':        'Ahmet Yılmaz',
        'cert_no':     'TÜRKAK-GBF-2024-1234',
        'cert_body':   'TKSD / TÜRKAK',
        'valid_until': '2026-12-31',
        'title':       'Kimyager'  (opsiyonel)
    }
    """
    errors = []
    warnings = []

    if not cert_data.get('name'):
        errors.append('Hazırlayıcı adı zorunludur.')

    if not cert_data.get('cert_no'):
        errors.append('Sertifika numarası zorunludur.')

    if not cert_data.get('cert_body'):
        warnings.append('Sertifika veren kurum belirtilmemiş.')

    # Geçerlilik tarihi kontrolü
    valid_until = cert_data.get('valid_until')
    is_expired = False
    if valid_until:
        try:
            exp_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
            if exp_date < date.today():
                is_expired = True
                errors.append(
                    f'Sertifika süresi dolmuş: {valid_until}. '
                    f'Yenilenmeden GBF yasal geçerlilik taşımaz.'
                )
            elif (exp_date - date.today()).days < 90:
                warnings.append(
                    f'Sertifika {(exp_date - date.today()).days} gün içinde dolacak.'
                )
        except ValueError:
            warnings.append('Geçerlilik tarihi formatı hatalı (YYYY-MM-DD olmalı).')

    return {
        'valid':      len(errors) == 0,
        'is_expired': is_expired,
        'errors':     errors,
        'warnings':   warnings,
    }


def format_author_block(cert_data: dict, lang: str = 'TR') -> str:
    """
    PDF Bölüm 16 için hazırlayıcı bilgi bloğu.
    """
    if not cert_data:
        if lang == 'TR':
            return (
                'UYARI: Bu form henüz sertifikalı bir GBF hazırlayıcısı tarafından '
                'onaylanmamıştır. KKDİK kapsamında yasal geçerliliği bulunmamaktadır.'
            )
        return (
            'WARNING: This SDS has not yet been validated by a certified SDS author. '
            'It has no legal validity under KKDİK.'
        )

    name       = cert_data.get('name', '—')
    cert_no    = cert_data.get('cert_no', '—')
    cert_body  = cert_data.get('cert_body', '—')
    valid_until = cert_data.get('valid_until', '—')
    title      = cert_data.get('title', '')

    if lang == 'TR':
        lines = [
            'GBF Hazırlayan / Onaylayan:',
            f'  Ad Soyad      : {name}' + (f' ({title})' if title else ''),
            f'  Sertifika No  : {cert_no}',
            f'  Veren Kurum   : {cert_body}',
            f'  Geçerlilik    : {valid_until}',
            '',
            'Bu GBF KKDİK Ek-2 formatına uygun olarak hazırlanmış ve '
            'sertifikalı hazırlayıcı tarafından onaylanmıştır.',
        ]
    else:
        lines = [
            'Prepared / Approved by:',
            f'  Name          : {name}' + (f' ({title})' if title else ''),
            f'  Certificate   : {cert_no}',
            f'  Issuing Body  : {cert_body}',
            f'  Valid Until   : {valid_until}',
            '',
            'This SDS has been prepared in compliance with KKDİK Annex-2 '
            'and approved by a certified SDS author.',
        ]

    return '\n'.join(lines)


def get_default_author() -> dict:
    """
    Kullanıcı sertifika girmemişse gösterilecek varsayılan uyarı bloğu.
    """
    return {
        'name':        '',
        'cert_no':     '',
        'cert_body':   '',
        'valid_until': '',
        '_missing':    True,
    }


if __name__ == '__main__':
    cert = {
        'name': 'Dr. Ayşe Kaya',
        'cert_no': 'TÜRKAK-GBF-2024-0042',
        'cert_body': 'TKSD',
        'valid_until': '2026-06-30',
        'title': 'Kimya Mühendisi'
    }
    result = validate_certificate(cert)
    print('Doğrulama:', result)
    print()
    print(format_author_block(cert, lang='TR'))
