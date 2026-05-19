-- =====================================================================
-- KX_ CƏDVƏLLƏRİ — Kənar serverdən sinxronizasiya üçün
-- Bu faylı database.sql-dən SONRA ayrıca import edin
-- və ya database.sql-in sonuna əlavə edin
-- =====================================================================

CREATE TABLE IF NOT EXISTS `kx_bolgeler` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ad` varchar(150) NOT NULL,
  `nov` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ad` (`ad`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `kx_rayonlar` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ad` varchar(150) NOT NULL,
  `bolge_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ad_bolge` (`ad`, `bolge_id`),
  KEY `bolge_id` (`bolge_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `kx_muessiseler` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ad` varchar(200) NOT NULL,
  `bolge_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ad_bolge` (`ad`, `bolge_id`),
  KEY `bolge_id` (`bolge_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `kx_hekimler` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pg_id` int(11) NOT NULL COMMENT 'Kənar serverdəki ID',
  `ad_soyad` varchar(200) NOT NULL,
  `ixtisas_kod` varchar(20) DEFAULT NULL,
  `kateqoriya` varchar(10) DEFAULT NULL,
  `derece` varchar(20) DEFAULT NULL,
  `cinsiyyet` varchar(10) DEFAULT NULL,
  `bolge_id` int(11) DEFAULT NULL,
  `rayon_id` int(11) DEFAULT NULL,
  `muessise_id` int(11) DEFAULT NULL,
  `son_sinx` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `pg_id` (`pg_id`),
  KEY `bolge_id` (`bolge_id`),
  KEY `rayon_id` (`rayon_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
