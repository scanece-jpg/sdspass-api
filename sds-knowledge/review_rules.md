# Denetim Düzeltme Kuralları

Bu dosya, tespit edilen denetim hatalarından üretilen ve kullanıcı tarafından onaylanan kalıcı kurallardır.
Her kural bir sonraki denetimde otomatik olarak system prompt'a eklenir.

- B11'de ATEmix inhalasyon hesabı varsa (örn. "İnhalasyon: 20.0 mg/L/4h → H332"), bileşen H331 olsa bile karışım H332 çıkabilir — bu normaldir, gerekçesizlik değildir; B11 hesabı gerekçenin kendisidir.
- B3.2'deki bileşen H kodları († işaretliler dahil) bileşenin kendi sınıflandırmasıdır; B2.1'deki karışım H kodlarından farklı olması beklenen bir durumdur, çelişki değildir.
- Mevzuat ifadesinde "verilir / sağlanır / bulunur" gibi geniş zaman kipindeki fiiller zorunlu gereklilik, "sağlanabilir / verilebilir / eklenebilir" gibi gereklilik kipi opsiyonel gereklilik anlamına gelir; ikisini aynı ağırlıkta hata olarak raporlama.
- SDS metninde geçmeyen terim, kısaltma veya alan adı rapora yazılmaz; bulgu oluşturmadan önce ilgili ifadenin belgede gerçekten yer aldığını doğrula.
- Belge üst bilgisindeki (header/metadata) H-kodu özeti ile B2.1 tam sınıflandırma tablosu karşılaştırılmalıdır; başlık alanı eksik H kodu içeriyorsa bulgu "B2.1 içinde çelişki" değil "başlık ile B2.1 tutarsızlığı" olarak tanımlanmalıdır.
