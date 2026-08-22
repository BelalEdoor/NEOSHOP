-- MySQL dump 10.13  Distrib 9.6.0, for macos14.8 (x86_64)
--
-- Host: localhost    Database: neoshop_db
-- ------------------------------------------------------
-- Server version	9.6.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '210fa29a-41b3-11f1-91f6-420b71172059:1-3187';

--
-- Table structure for table `allergens`
--

DROP TABLE IF EXISTS `allergens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `allergens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_ar` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_allergens_name` (`name`),
  KEY `ix_allergens_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `allergens`
--

LOCK TABLES `allergens` WRITE;
/*!40000 ALTER TABLE `allergens` DISABLE KEYS */;
INSERT INTO `allergens` VALUES (1,'milk','الحليب'),(2,'nuts','المكسرات'),(3,'peanuts','الفول السوداني'),(4,'gluten','الغلوتين'),(5,'eggs','البيض'),(6,'soy','فول الصويا'),(7,'fish','الأسماك'),(8,'shellfish','المحاريات والقشريات'),(9,'sesame','السمسم'),(10,'sulfites','الكبريتات'),(11,'fruits','الفواكه'),(12,'spices','التوابل والفلفل الحار');
/*!40000 ALTER TABLE `allergens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cart_items`
--

DROP TABLE IF EXISTS `cart_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cart_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int NOT NULL,
  `product_id` int NOT NULL,
  `quantity` int DEFAULT NULL,
  `unit_price` float NOT NULL,
  `added_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `session_id` (`session_id`),
  KEY `product_id` (`product_id`),
  KEY `ix_cart_items_id` (`id`),
  CONSTRAINT `cart_items_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `shopping_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `cart_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=214 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cart_items`
--

LOCK TABLES `cart_items` WRITE;
/*!40000 ALTER TABLE `cart_items` DISABLE KEYS */;
INSERT INTO `cart_items` VALUES (169,55,1447,1,13.17,'2026-08-03 20:37:19'),(170,56,1447,2,13.17,'2026-08-03 20:37:32'),(173,57,1466,1,24.02,'2026-08-03 21:50:05'),(174,58,1466,1,24.02,'2026-08-03 22:02:46'),(177,59,1505,1,6.19,'2026-08-03 22:07:42'),(179,59,1303,1,22.59,'2026-08-03 22:08:06'),(181,61,1505,1,6.19,'2026-08-03 22:35:23'),(182,61,1352,3,23.19,'2026-08-03 22:49:04'),(184,61,1449,1,11.21,'2026-08-03 22:49:11'),(185,61,1353,5,11.56,'2026-08-03 22:50:36'),(186,61,1354,3,7.42,'2026-08-03 22:50:50'),(188,62,1352,1,23.19,'2026-08-04 20:50:57'),(190,62,1303,1,22.59,'2026-08-04 20:51:07'),(191,64,1272,1,8.95,'2026-08-11 00:57:00'),(193,64,1363,1,14.2,'2026-08-11 00:59:11'),(198,66,1449,1,11.21,'2026-08-13 15:36:01'),(199,66,1354,1,7.42,'2026-08-13 15:36:17'),(201,67,1352,1,23.19,'2026-08-13 15:39:09'),(203,68,1347,1,3.4,'2026-08-13 15:40:17'),(207,69,1352,1,23.19,'2026-08-13 15:42:54'),(210,76,1280,1,17.17,'2026-08-19 11:30:02'),(211,76,1352,1,23.19,'2026-08-19 11:30:27'),(212,82,1272,1,8.95,'2026-08-21 19:09:23'),(213,82,1364,1,19.42,'2026-08-21 19:09:48');
/*!40000 ALTER TABLE `cart_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cart_live_status`
--

DROP TABLE IF EXISTS `cart_live_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cart_live_status` (
  `cart_id` int NOT NULL,
  `current_section_id` int DEFAULT NULL,
  `pos_x` float DEFAULT NULL,
  `pos_y` float DEFAULT NULL,
  `last_marker_id` int DEFAULT NULL,
  `updated_at` datetime DEFAULT (now()),
  PRIMARY KEY (`cart_id`),
  KEY `current_section_id` (`current_section_id`),
  CONSTRAINT `cart_live_status_ibfk_1` FOREIGN KEY (`cart_id`) REFERENCES `carts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `cart_live_status_ibfk_2` FOREIGN KEY (`current_section_id`) REFERENCES `sections` (`section_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cart_live_status`
--

LOCK TABLES `cart_live_status` WRITE;
/*!40000 ALTER TABLE `cart_live_status` DISABLE KEYS */;
INSERT INTO `cart_live_status` VALUES (1,3,450,200,3,'2026-07-06 21:03:19');
/*!40000 ALTER TABLE `cart_live_status` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `carts`
--

DROP TABLE IF EXISTS `carts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `carts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cart_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `rfid_uid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('ACTIVE','PENDING_PAYMENT','PAYMENT_IN_PROGRESS','PAID','CANCELLED','FAILED') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `cart_number` (`cart_number`),
  UNIQUE KEY `ix_carts_rfid_uid` (`rfid_uid`),
  KEY `ix_carts_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `carts`
--

LOCK TABLES `carts` WRITE;
/*!40000 ALTER TABLE `carts` DISABLE KEYS */;
INSERT INTO `carts` VALUES (1,'CART-001','RFID-DEFAULT-001','ACTIVE','2026-07-05 00:18:20'),(2,'CART-002','RFID-DEFAULT-002','ACTIVE','2026-07-05 00:18:20');
/*!40000 ALTER TABLE `carts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `customer_allergies`
--

DROP TABLE IF EXISTS `customer_allergies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customer_allergies` (
  `user_id` int NOT NULL,
  `allergen_id` int NOT NULL,
  PRIMARY KEY (`user_id`,`allergen_id`),
  KEY `allergen_id` (`allergen_id`),
  CONSTRAINT `customer_allergies_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `customer_allergies_ibfk_2` FOREIGN KEY (`allergen_id`) REFERENCES `allergens` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `customer_allergies`
--

LOCK TABLES `customer_allergies` WRITE;
/*!40000 ALTER TABLE `customer_allergies` DISABLE KEYS */;
INSERT INTO `customer_allergies` VALUES (3,1),(4,1),(13,1),(14,1),(5,2),(6,2),(9,2),(12,2),(13,2),(14,2),(3,3),(8,3),(3,5),(4,5),(8,5),(9,5),(13,5),(14,5),(5,6),(6,6),(8,6),(12,6),(14,6),(12,7),(13,7),(14,7),(14,8),(5,9),(8,9),(14,10),(14,11),(14,12);
/*!40000 ALTER TABLE `customer_allergies` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `customer_health_conditions`
--

DROP TABLE IF EXISTS `customer_health_conditions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customer_health_conditions` (
  `user_id` int NOT NULL,
  `condition_id` int NOT NULL,
  `severity` enum('mild','moderate','severe') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`user_id`,`condition_id`),
  KEY `condition_id` (`condition_id`),
  CONSTRAINT `customer_health_conditions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `customer_health_conditions_ibfk_2` FOREIGN KEY (`condition_id`) REFERENCES `health_conditions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `customer_health_conditions`
--

LOCK TABLES `customer_health_conditions` WRITE;
/*!40000 ALTER TABLE `customer_health_conditions` DISABLE KEYS */;
INSERT INTO `customer_health_conditions` VALUES (3,1,'moderate'),(10,1,'moderate'),(11,1,'moderate'),(12,2,'moderate'),(13,1,'moderate'),(14,3,'moderate');
/*!40000 ALTER TABLE `customer_health_conditions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `health_conditions`
--

DROP TABLE IF EXISTS `health_conditions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_conditions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_ar` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `related_nutrient` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warning_threshold` decimal(6,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `ix_health_conditions_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `health_conditions`
--

LOCK TABLES `health_conditions` WRITE;
/*!40000 ALTER TABLE `health_conditions` DISABLE KEYS */;
INSERT INTO `health_conditions` VALUES (1,'Diabetes','السكري','sugar',15.00),(2,'Hypertension','ضغط الدم','sodium',400.00),(3,'Obesity','السمنة','calories',300.00);
/*!40000 ALTER TABLE `health_conditions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `invoices`
--

DROP TABLE IF EXISTS `invoices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `invoices` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `session_id` int DEFAULT NULL,
  `cart_rfid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subtotal` float DEFAULT NULL,
  `discount` float DEFAULT NULL,
  `total_amount` float DEFAULT NULL,
  `status` enum('CREATED','SENT','PROCESSING','PAID','CANCELLED') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `items_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT (now()),
  `paid_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_invoices_invoice_code` (`invoice_code`),
  KEY `session_id` (`session_id`),
  KEY `ix_invoices_id` (`id`),
  KEY `ix_invoices_cart_rfid` (`cart_rfid`),
  CONSTRAINT `invoices_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `shopping_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `invoices`
--

LOCK TABLES `invoices` WRITE;
/*!40000 ALTER TABLE `invoices` DISABLE KEYS */;
INSERT INTO `invoices` VALUES (1,'INV-20260705-0001',2,NULL,3.4,0,3.4,'SENT','[{\"product_id\": 1, \"product_name\": \"Whole Milk 1L\", \"barcode\": \"6001001001001\", \"unit_price\": 1.5, \"quantity\": 1, \"subtotal\": 1.5}, {\"product_id\": 16, \"product_name\": \"Baby Spinach 150g\", \"barcode\": \"6001005001002\", \"unit_price\": 1.9, \"quantity\": 1, \"subtotal\": 1.9}]','2026-07-05 00:23:57',NULL),(2,'INV-20260706-0001',6,NULL,3.5,0,3.5,'SENT','[{\"product_id\": 15, \"product_name\": \"Organic Eggs x12\", \"barcode\": \"6001005001001\", \"unit_price\": 3.5, \"quantity\": 1, \"subtotal\": 3.5}]','2026-07-06 09:55:26',NULL),(3,'INV-20260706-0002',9,NULL,15.5,0,15.5,'SENT','[{\"product_id\": 20, \"product_name\": \"Extra Virgin Olive Oil 500ml\", \"barcode\": \"6001007001002\", \"unit_price\": 6.5, \"quantity\": 1, \"subtotal\": 6.5}, {\"product_id\": 8, \"product_name\": \"Mixed Nuts 200g\", \"barcode\": \"6001003001001\", \"unit_price\": 4.5, \"quantity\": 2, \"subtotal\": 9.0}]','2026-07-06 20:32:09',NULL),(4,'INV-20260707-0001',16,NULL,9.1,0,9.1,'SENT','[{\"product_id\": 20, \"product_name\": \"Extra Virgin Olive Oil 500ml\", \"barcode\": \"6001007001002\", \"unit_price\": 6.5, \"quantity\": 1, \"subtotal\": 6.5}, {\"product_id\": 13, \"product_name\": \"Oat Milk 1L\", \"barcode\": \"6001004001003\", \"unit_price\": 2.6, \"quantity\": 1, \"subtotal\": 2.6}]','2026-07-07 10:50:09',NULL),(5,'INV-20260710-0001',19,NULL,1.5,0,1.5,'SENT','[{\"product_id\": 1, \"product_name\": \"Whole Milk 1L\", \"barcode\": \"6001001001001\", \"unit_price\": 1.5, \"quantity\": 1, \"subtotal\": 1.5}]','2026-07-10 16:24:07',NULL),(6,'INV-20260711-0001',22,NULL,6.5,0,6.5,'SENT','[{\"product_id\": 20, \"product_name\": \"Extra Virgin Olive Oil 500ml\", \"barcode\": \"6001007001002\", \"unit_price\": 6.5, \"quantity\": 1, \"subtotal\": 6.5}]','2026-07-11 13:17:19',NULL),(7,'INV-20260730-0001',42,NULL,22.18,0,22.18,'SENT','[{\"product_id\": 22, \"product_name\": \"Whole Milk 1L\", \"barcode\": \"100000000001\", \"unit_price\": 8.95, \"quantity\": 1, \"subtotal\": 8.95}, {\"product_id\": 187, \"product_name\": \"Tuna\", \"barcode\": \"100000000166\", \"unit_price\": 13.23, \"quantity\": 1, \"subtotal\": 13.23}]','2026-07-30 10:39:27',NULL),(8,'INV-20260803-0001',59,NULL,28.78,0,28.78,'SENT','[{\"product_id\": 1505, \"product_name\": \"Toast Bread\", \"barcode\": \"100000000234\", \"unit_price\": 6.19, \"quantity\": 1, \"subtotal\": 6.19}, {\"product_id\": 1303, \"product_name\": \"Banana\", \"barcode\": \"100000000032\", \"unit_price\": 22.59, \"quantity\": 1, \"subtotal\": 22.59}]','2026-08-03 22:08:09',NULL),(9,'INV-20260813-0001',67,NULL,23.19,0,23.19,'SENT','[{\"product_id\": 1352, \"product_name\": \"Dark Chocolate\", \"barcode\": \"100000000081\", \"unit_price\": 23.19, \"quantity\": 1, \"subtotal\": 23.19}]','2026-08-13 15:39:14',NULL),(10,'INV-20260813-0002',69,NULL,23.19,0,23.19,'SENT','[{\"product_id\": 1352, \"product_name\": \"Dark Chocolate\", \"barcode\": \"100000000081\", \"unit_price\": 23.19, \"quantity\": 1, \"subtotal\": 23.19}]','2026-08-13 15:43:04',NULL);
/*!40000 ALTER TABLE `invoices` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `marker_read_log`
--

DROP TABLE IF EXISTS `marker_read_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `marker_read_log` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `cart_id` int NOT NULL,
  `marker_id` int NOT NULL,
  `detected_at` datetime DEFAULT (now()),
  PRIMARY KEY (`log_id`),
  KEY `cart_id` (`cart_id`),
  CONSTRAINT `marker_read_log_ibfk_1` FOREIGN KEY (`cart_id`) REFERENCES `carts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `marker_read_log`
--

LOCK TABLES `marker_read_log` WRITE;
/*!40000 ALTER TABLE `marker_read_log` DISABLE KEYS */;
INSERT INTO `marker_read_log` VALUES (1,1,3,'2026-07-06 21:03:19');
/*!40000 ALTER TABLE `marker_read_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payment_transactions`
--

DROP TABLE IF EXISTS `payment_transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `payment_id` int NOT NULL,
  `transaction_type` enum('COIN','BILL') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `denomination` float NOT NULL,
  `count` int DEFAULT NULL,
  `total_value` float NOT NULL,
  `inserted_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `payment_id` (`payment_id`),
  KEY `ix_payment_transactions_id` (`id`),
  CONSTRAINT `payment_transactions_ibfk_1` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_transactions`
--

LOCK TABLES `payment_transactions` WRITE;
/*!40000 ALTER TABLE `payment_transactions` DISABLE KEYS */;
/*!40000 ALTER TABLE `payment_transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payments`
--

DROP TABLE IF EXISTS `payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `total_due` float NOT NULL,
  `amount_inserted` float DEFAULT NULL,
  `change_returned` float DEFAULT NULL,
  `method` enum('CASH','COIN','MIXED') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('PENDING','IN_PROGRESS','COMPLETED','FAILED','REFUNDED') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cart_rfid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `esp32_device_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT (now()),
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `invoice_id` (`invoice_id`),
  KEY `ix_payments_id` (`id`),
  CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payments`
--

LOCK TABLES `payments` WRITE;
/*!40000 ALTER TABLE `payments` DISABLE KEYS */;
/*!40000 ALTER TABLE `payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `product_allergens`
--

DROP TABLE IF EXISTS `product_allergens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_allergens` (
  `product_id` int NOT NULL,
  `allergen_id` int NOT NULL,
  PRIMARY KEY (`product_id`,`allergen_id`),
  KEY `allergen_id` (`allergen_id`),
  CONSTRAINT `product_allergens_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `product_allergens_ibfk_2` FOREIGN KEY (`allergen_id`) REFERENCES `allergens` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `product_allergens`
--

LOCK TABLES `product_allergens` WRITE;
/*!40000 ALTER TABLE `product_allergens` DISABLE KEYS */;
INSERT INTO `product_allergens` VALUES (1272,1),(1273,1),(1274,1),(1275,1),(1276,1),(1277,1),(1278,1),(1279,1),(1280,1),(1281,1),(1282,1),(1283,1),(1284,1),(1285,1),(1286,1),(1287,1),(1288,1),(1289,1),(1378,1),(1379,1),(1380,1),(1381,1),(1382,1),(1383,1),(1384,1),(1385,1),(1386,1),(1387,1),(1388,1),(1389,1),(1390,1),(1391,1),(1392,1),(1393,1),(1394,1),(1395,1),(1484,1),(1485,1),(1486,1),(1487,1),(1488,1),(1489,1),(1490,1),(1491,1),(1492,1),(1493,1),(1494,1),(1495,1),(1496,1),(1497,1),(1498,1),(1499,1),(1500,1),(1501,1),(1276,2),(1357,2),(1358,2),(1359,2),(1360,2),(1361,2),(1382,2),(1463,2),(1464,2),(1465,2),(1466,2),(1467,2),(1488,2),(1361,3),(1467,3),(1290,4),(1291,4),(1292,4),(1293,4),(1294,4),(1295,4),(1296,4),(1297,4),(1298,4),(1299,4),(1300,4),(1301,4),(1336,4),(1337,4),(1338,4),(1341,4),(1396,4),(1397,4),(1398,4),(1399,4),(1400,4),(1401,4),(1402,4),(1403,4),(1404,4),(1405,4),(1406,4),(1407,4),(1442,4),(1443,4),(1444,4),(1447,4),(1502,4),(1503,4),(1504,4),(1505,4),(1506,4),(1507,4),(1508,4),(1509,4),(1510,4),(1511,4),(1512,4),(1513,4),(1278,6),(1341,6),(1384,6),(1447,6),(1490,6),(1330,7),(1331,7),(1436,7),(1437,7);
/*!40000 ALTER TABLE `product_allergens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `products`
--

DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_ar` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `price` float NOT NULL,
  `barcode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  `category` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subcategory` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cv_category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `brand` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `ingredients` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `allergens` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `image_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `location_x` int DEFAULT NULL,
  `location_y` int DEFAULT NULL,
  `section` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sugar_g` float DEFAULT NULL,
  `sodium_mg` float DEFAULT NULL,
  `calories` float DEFAULT NULL,
  `protein_g` float DEFAULT NULL,
  `fat_g` float DEFAULT NULL,
  `saturated_fat_g` float DEFAULT NULL,
  `carbohydrates_g` float DEFAULT NULL,
  `fiber_g` float DEFAULT NULL,
  `cholesterol_mg` float DEFAULT NULL,
  `is_vegan` tinyint(1) DEFAULT '0',
  `is_vegetarian` tinyint(1) DEFAULT '0',
  `is_gluten_free` tinyint(1) DEFAULT '0',
  `is_lactose_free` tinyint(1) DEFAULT '0',
  `is_on_offer` tinyint(1) NOT NULL,
  `old_price` float DEFAULT NULL,
  `offer_expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_products_barcode` (`barcode`),
  KEY `ix_products_id` (`id`),
  KEY `ix_products_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=1522 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `products`
--

LOCK TABLES `products` WRITE;
/*!40000 ALTER TABLE `products` DISABLE KEYS */;
INSERT INTO `products` VALUES (1272,'Whole Milk 1L',NULL,8.95,'100000000001',100,'Dairy','Milk',NULL,'Lurpak','Whole Milk 1L','See package','Milk',NULL,8,5,'Dairy',3.9,475,283,29.4,19.5,6.4,17.2,2.2,96,0,1,1,0,0,NULL,NULL),(1273,'Low Fat Milk 1L',NULL,17.24,'100000000002',100,'Dairy','Milk',NULL,'FreshFarm','Low Fat Milk 1L','See package','Milk',NULL,10,3,'Dairy',11,590,41,16.5,5.6,8.8,8.2,3.3,76,0,1,1,0,0,NULL,NULL),(1274,'Skim Milk 1L',NULL,15.85,'100000000003',100,'Dairy','Milk',NULL,'Arla','Skim Milk 1L','See package','Milk',NULL,1,1,'Dairy',5.8,291,393,15.5,22.6,5.3,34.6,7.3,76,0,1,1,0,0,NULL,NULL),(1275,'Lactose Free Milk',NULL,13.59,'100000000004',100,'Dairy','Milk',NULL,'Arla','Lactose Free Milk','See package','Milk',NULL,9,7,'Dairy',1.7,400,317,2.3,26,3.2,56,4.4,97,0,1,1,0,0,NULL,NULL),(1276,'Almond Milk',NULL,2.55,'100000000005',100,'Dairy','Milk',NULL,'Arla','Almond Milk','See package','Milk',NULL,9,2,'Dairy',13.8,627,456,14.2,19.7,9.4,15.1,3,77,0,1,1,0,0,NULL,NULL),(1277,'Oat Milk',NULL,7.93,'100000000006',100,'Dairy','Milk',NULL,'Lurpak','Oat Milk','See package','Milk',NULL,4,1,'Dairy',0.1,214,426,8.8,17.5,2.7,31.4,3.8,6,0,1,1,0,0,NULL,NULL),(1278,'Soy Milk',NULL,13.59,'100000000007',100,'Dairy','Milk',NULL,'Arla','Soy Milk','See package','Milk',NULL,1,2,'Dairy',13.4,178,397,19.6,2.8,0.1,41.2,10,50,0,1,1,0,0,NULL,NULL),(1279,'Greek Yogurt',NULL,24.76,'100000000008',100,'Dairy','Yogurt',NULL,'Arla','Greek Yogurt','See package','Milk',NULL,7,6,'Dairy',16,196,382,29,6.7,1.2,19.4,7.6,22,0,1,1,0,0,NULL,NULL),(1280,'Strawberry Yogurt',NULL,17.17,'100000000009',100,'Dairy','Yogurt',NULL,'President','Strawberry Yogurt','See package','Milk',NULL,10,5,'Dairy',8.4,211,142,12.3,20.4,2.7,32.4,5.8,57,0,1,1,0,0,NULL,NULL),(1281,'Vanilla Yogurt',NULL,4.25,'100000000010',100,'Dairy','Yogurt',NULL,'FreshFarm','Vanilla Yogurt','See package','Milk',NULL,10,2,'Dairy',13.9,621,250,29.4,2.4,6.4,50.1,0.3,92,0,1,1,0,0,NULL,NULL),(1282,'Labneh',NULL,19.3,'100000000011',100,'Dairy','Yogurt',NULL,'FreshFarm','Labneh','See package','Milk',NULL,2,3,'Dairy',4.1,592,274,11.2,11.3,9.4,7.9,0.3,63,0,1,1,0,0,NULL,NULL),(1283,'Cheddar Cheese',NULL,8.34,'100000000012',100,'Dairy','Cheese',NULL,'Alpro','Cheddar Cheese','See package','Milk',NULL,2,3,'Dairy',19,437,167,27.4,10.7,2.6,44.4,6.8,46,0,1,1,0,0,NULL,NULL),(1284,'Mozzarella',NULL,9.05,'100000000013',100,'Dairy','Cheese',NULL,'Alpro','Mozzarella','See package','Milk',NULL,9,9,'Dairy',1.1,557,76,17.5,24,4.4,26.8,1.5,78,0,1,1,0,0,NULL,NULL),(1285,'Cream Cheese',NULL,12.74,'100000000014',100,'Dairy','Cheese',NULL,'Lurpak','Cream Cheese','See package','Milk',NULL,7,3,'Dairy',8,364,253,8,24.8,3,47.6,4.5,40,0,1,1,0,0,NULL,NULL),(1286,'Feta',NULL,6.59,'100000000015',100,'Dairy','Cheese',NULL,'Lurpak','Feta','See package','Milk',NULL,10,1,'Dairy',11.9,207,43,19.2,22.6,6.1,5.4,9.6,115,0,1,1,0,0,NULL,NULL),(1287,'Parmesan',NULL,11.8,'100000000016',100,'Dairy','Cheese',NULL,'FreshFarm','Parmesan','See package','Milk',NULL,4,9,'Dairy',4.9,660,293,8.1,3.8,8.8,34.8,3.9,38,0,1,1,0,0,NULL,NULL),(1288,'Salted Butter',NULL,22.08,'100000000017',100,'Dairy','Butter',NULL,'FreshFarm','Salted Butter','See package','Milk',NULL,7,9,'Dairy',6.4,659,289,29.6,23.3,8.3,21.8,0.4,23,0,1,1,0,0,NULL,NULL),(1289,'Unsalted Butter',NULL,20.13,'100000000018',100,'Dairy','Butter',NULL,'Lurpak','Unsalted Butter','See package','Milk',NULL,5,7,'Dairy',8.1,291,390,1.2,9.6,5.3,48.1,6.1,7,0,1,1,0,0,NULL,NULL),(1290,'White Bread',NULL,8.26,'100000000019',100,'Bakery','Bread',NULL,'Golden Bakery','White Bread','See package',NULL,NULL,3,3,'Bakery',1.2,681,222,10.2,19.5,6.8,20.5,4.3,77,0,1,0,1,0,NULL,NULL),(1291,'Whole Wheat Bread',NULL,13.04,'100000000020',100,'Bakery','Bread',NULL,'Golden Bakery','Whole Wheat Bread','See package',NULL,NULL,3,7,'Bakery',12,513,261,25.6,26.1,4.8,41.9,5.7,15,0,1,0,1,0,NULL,NULL),(1292,'Brown Bread',NULL,22.73,'100000000021',100,'Bakery','Bread',NULL,'Golden Bakery','Brown Bread','See package',NULL,NULL,2,10,'Bakery',9.8,358,380,17.9,19.9,2.8,9,3.4,68,0,1,0,1,0,NULL,NULL),(1293,'Toast Bread',NULL,15.86,'100000000022',100,'Bakery','Bread',NULL,'Golden Bakery','Toast Bread','See package',NULL,NULL,5,8,'Bakery',11.3,697,290,17.1,2.3,5.2,42.9,9.6,22,0,1,0,1,0,NULL,NULL),(1294,'Pita Bread',NULL,21.9,'100000000023',100,'Bakery','Bread',NULL,'Golden Bakery','Pita Bread','See package',NULL,NULL,9,2,'Bakery',17.7,246,176,27.1,11.3,3.2,40.4,3.1,67,0,1,0,1,0,NULL,NULL),(1295,'Sourdough',NULL,15.27,'100000000024',100,'Bakery','Bread',NULL,'Wonder','Sourdough','See package',NULL,NULL,2,10,'Bakery',2.9,480,330,20,1.8,8.8,48.4,6.6,99,0,1,0,1,0,NULL,NULL),(1296,'Burger Buns',NULL,4.91,'100000000025',100,'Bakery','Bread',NULL,'Wonder','Burger Buns','See package',NULL,NULL,2,2,'Bakery',11.7,402,204,24.5,15.4,8.4,7.6,4.1,85,0,1,0,1,0,NULL,NULL),(1297,'Hot Dog Buns',NULL,8.01,'100000000026',100,'Bakery','Bread',NULL,'Golden Bakery','Hot Dog Buns','See package',NULL,NULL,4,4,'Bakery',13.2,305,284,24.5,25.8,8.5,20.4,6.8,20,0,1,0,1,0,NULL,NULL),(1298,'Croissant',NULL,11.9,'100000000027',100,'Bakery','Pastry',NULL,'Golden Bakery','Croissant','See package',NULL,NULL,1,1,'Bakery',12,512,497,8.3,0.2,8.6,37.8,0,117,0,1,0,1,0,NULL,NULL),(1299,'Donut',NULL,8.49,'100000000028',100,'Bakery','Pastry',NULL,'Golden Bakery','Donut','See package',NULL,NULL,5,7,'Bakery',3.6,2,108,21.1,24,8.3,40.8,9.1,16,0,1,0,1,0,NULL,NULL),(1300,'Muffin',NULL,7.48,'100000000029',100,'Bakery','Pastry',NULL,'Golden Bakery','Muffin','See package',NULL,NULL,9,10,'Bakery',4.8,564,463,10.7,25.7,4.6,48.5,8.3,96,0,1,0,1,0,NULL,NULL),(1301,'Bagel',NULL,18.98,'100000000030',100,'Bakery','Pastry',NULL,'Golden Bakery','Bagel','See package',NULL,NULL,1,2,'Bakery',14.3,449,37,8.1,17,0.9,18.7,0.7,93,0,1,0,1,0,NULL,NULL),(1302,'Apple',NULL,20.74,'100000000031',100,'Produce','Fruit',NULL,'FreshFarm','Apple','See package',NULL,NULL,6,8,'Produce',13.6,392,182,6.9,10.6,0.3,0.7,9.8,90,1,1,1,1,0,NULL,NULL),(1303,'Banana',NULL,22.59,'100000000032',100,'Produce','Fruit',NULL,'FreshFarm','Banana','See package',NULL,NULL,7,2,'Produce',13.1,63,222,2.1,22.7,9.3,56.7,8.1,113,1,1,1,1,0,NULL,NULL),(1304,'Orange',NULL,21.56,'100000000033',100,'Produce','Fruit',NULL,'FreshFarm','Orange','See package',NULL,NULL,1,6,'Produce',1.3,166,239,7.3,25.5,8.7,48,8.5,119,1,1,1,1,0,NULL,NULL),(1305,'Pear',NULL,18.51,'100000000034',100,'Produce','Fruit',NULL,'FreshFarm','Pear','See package',NULL,NULL,1,10,'Produce',11.5,644,136,18.7,29.6,4,35.5,2.3,70,1,1,1,1,0,NULL,NULL),(1306,'Grapes',NULL,16.79,'100000000035',100,'Produce','Fruit',NULL,'FreshFarm','Grapes','See package',NULL,NULL,4,7,'Produce',6.3,16,41,26.3,12,1.9,47.4,2,86,1,1,1,1,0,NULL,NULL),(1307,'Mango',NULL,15.5,'100000000036',100,'Produce','Fruit',NULL,'FreshFarm','Mango','See package',NULL,NULL,9,9,'Produce',7.4,102,131,27.9,21.8,8.3,46.8,2.1,26,1,1,1,1,0,NULL,NULL),(1308,'Kiwi',NULL,21.5,'100000000037',100,'Produce','Fruit',NULL,'FreshFarm','Kiwi','See package',NULL,NULL,2,1,'Produce',1.5,190,485,18.8,12.7,8,6.8,3.6,63,1,1,1,1,0,NULL,NULL),(1309,'Pineapple',NULL,13.25,'100000000038',100,'Produce','Fruit',NULL,'FreshFarm','Pineapple','See package',NULL,NULL,2,8,'Produce',11.1,371,387,27.6,21.2,3,3.9,0.4,12,1,1,1,1,0,NULL,NULL),(1310,'Watermelon',NULL,5.57,'100000000039',100,'Produce','Fruit',NULL,'FreshFarm','Watermelon','See package',NULL,NULL,10,10,'Produce',17.5,22,341,22.6,2.5,7.7,40.9,1.9,31,1,1,1,1,0,NULL,NULL),(1311,'Lemon',NULL,12.22,'100000000040',100,'Produce','Fruit',NULL,'FreshFarm','Lemon','See package',NULL,NULL,2,8,'Produce',19.8,153,356,25,24.8,4.8,48,3.8,55,1,1,1,1,0,NULL,NULL),(1312,'Avocado',NULL,20.72,'100000000041',100,'Produce','Fruit',NULL,'FreshFarm','Avocado','See package',NULL,NULL,6,8,'Produce',12.7,100,423,10.9,0.2,7.5,51.1,0.6,72,1,1,1,1,0,NULL,NULL),(1313,'Tomato',NULL,20.38,'100000000042',100,'Produce','Vegetable',NULL,'FreshFarm','Tomato','See package',NULL,NULL,7,1,'Produce',15.2,521,20,5.1,3.4,6.3,21,9.9,33,1,1,1,1,0,NULL,NULL),(1314,'Potato',NULL,21.44,'100000000043',100,'Produce','Vegetable',NULL,'FreshFarm','Potato','See package',NULL,NULL,7,1,'Produce',14.9,308,226,1.4,22.5,9.3,45.6,2.6,25,1,1,1,1,0,NULL,NULL),(1315,'Onion',NULL,20.78,'100000000044',100,'Produce','Vegetable',NULL,'FreshFarm','Onion','See package',NULL,NULL,8,3,'Produce',6.8,383,89,2.9,24.1,0.1,53.5,8.2,29,1,1,1,1,0,NULL,NULL),(1316,'Garlic',NULL,9.46,'100000000045',100,'Produce','Vegetable',NULL,'FreshFarm','Garlic','See package',NULL,NULL,2,8,'Produce',16.1,419,31,12.7,21.6,6.8,7.1,7.2,11,1,1,1,1,0,NULL,NULL),(1317,'Carrot',NULL,16.46,'100000000046',100,'Produce','Vegetable',NULL,'FreshFarm','Carrot','See package',NULL,NULL,4,2,'Produce',19.3,373,411,17.5,26.5,3.3,3.7,6.8,88,1,1,1,1,0,NULL,NULL),(1318,'Cucumber',NULL,11.13,'100000000047',100,'Produce','Vegetable',NULL,'FreshFarm','Cucumber','See package',NULL,NULL,3,3,'Produce',8.6,632,446,7,3.3,7.5,54.2,3.5,10,1,1,1,1,0,NULL,NULL),(1319,'Broccoli',NULL,20.92,'100000000048',100,'Produce','Vegetable',NULL,'FreshFarm','Broccoli','See package',NULL,NULL,3,3,'Produce',16.5,557,404,21.1,28.1,8.2,44.9,0.5,13,1,1,1,1,0,NULL,NULL),(1320,'Spinach',NULL,15.58,'100000000049',100,'Produce','Vegetable',NULL,'FreshFarm','Spinach','See package',NULL,NULL,2,2,'Produce',5.2,76,424,28.3,2.4,4.3,50.3,7.1,56,1,1,1,1,0,NULL,NULL),(1321,'Lettuce',NULL,24.19,'100000000050',100,'Produce','Vegetable',NULL,'FreshFarm','Lettuce','See package',NULL,NULL,8,5,'Produce',10.6,339,198,19.6,21.5,3,27.9,5.9,48,1,1,1,1,0,NULL,NULL),(1322,'Bell Pepper',NULL,23.88,'100000000051',100,'Produce','Vegetable',NULL,'FreshFarm','Bell Pepper','See package',NULL,NULL,6,3,'Produce',8.1,698,259,25.5,17.9,0.4,45.8,6.1,46,1,1,1,1,0,NULL,NULL),(1323,'Chicken Breast',NULL,8.8,'100000000052',100,'Meat','Poultry',NULL,'Tyson','Chicken Breast','See package',NULL,NULL,3,10,'Meat',15.6,105,221,13.7,29.9,7,39,6.1,69,0,0,1,1,0,NULL,NULL),(1324,'Chicken Thigh',NULL,19.63,'100000000053',100,'Meat','Poultry',NULL,'Tyson','Chicken Thigh','See package',NULL,NULL,10,9,'Meat',17.1,642,101,30,17.9,4.7,12.9,8.7,59,0,0,1,1,0,NULL,NULL),(1325,'Chicken Wings',NULL,8.52,'100000000054',100,'Meat','Poultry',NULL,'Tyson','Chicken Wings','See package',NULL,NULL,9,2,'Meat',19.7,344,435,8.9,0.8,1.4,18.8,9,43,0,0,1,1,0,NULL,NULL),(1326,'Ground Chicken',NULL,6.37,'100000000055',100,'Meat','Poultry',NULL,'Tyson','Ground Chicken','See package',NULL,NULL,8,3,'Meat',19.7,437,215,0.7,3,4.2,59.7,8.5,120,0,0,1,1,0,NULL,NULL),(1327,'Beef Steak',NULL,7.43,'100000000056',100,'Meat','Beef',NULL,'FreshFarm','Beef Steak','See package',NULL,NULL,5,4,'Meat',6.3,379,144,6.4,23.3,2.3,47,2.2,87,0,0,1,1,0,NULL,NULL),(1328,'Ground Beef',NULL,18.03,'100000000057',100,'Meat','Beef',NULL,'Tyson','Ground Beef','See package',NULL,NULL,3,4,'Meat',5.1,107,336,2.4,15,9.8,1.5,4.1,109,0,0,1,1,0,NULL,NULL),(1329,'Beef Burger',NULL,3.72,'100000000058',100,'Meat','Beef',NULL,'FreshFarm','Beef Burger','See package',NULL,NULL,6,5,'Meat',0.7,355,223,24.7,11.2,4.7,16.4,8,39,0,0,1,1,0,NULL,NULL),(1330,'Salmon',NULL,22.37,'100000000059',100,'Meat','Seafood',NULL,'Tyson','Salmon','See package',NULL,NULL,10,10,'Meat',8,549,411,1.1,8.9,5.9,30.2,7.6,15,0,0,1,1,0,NULL,NULL),(1331,'Tuna',NULL,15.43,'100000000060',100,'Meat','Seafood',NULL,'Tyson','Tuna','See package',NULL,NULL,10,9,'Meat',12.7,299,176,10,26.3,5.1,38.9,1.6,24,0,0,1,1,0,NULL,NULL),(1332,'Shrimp',NULL,22.76,'100000000061',100,'Meat','Seafood',NULL,'Tyson','Shrimp','See package',NULL,NULL,8,6,'Meat',0.8,241,80,5.1,25.9,6.5,9.5,7.5,66,0,0,1,1,0,NULL,NULL),(1333,'White Rice',NULL,16,'100000000062',100,'Pantry','Rice',NULL,'Barilla','White Rice','See package',NULL,NULL,3,3,'Pantry',8.2,52,489,8.1,21.2,4.6,2.9,4.9,21,1,1,1,1,0,NULL,NULL),(1334,'Brown Rice',NULL,2.02,'100000000063',100,'Pantry','Rice',NULL,'Knorr','Brown Rice','See package',NULL,NULL,7,8,'Pantry',18.9,458,429,12,6.2,9.9,20.5,2.8,25,1,1,1,1,0,NULL,NULL),(1335,'Basmati Rice',NULL,17.05,'100000000064',100,'Pantry','Rice',NULL,'Heinz','Basmati Rice','See package',NULL,NULL,9,2,'Pantry',5,466,180,8.3,0.9,4.9,28.7,6.1,21,1,1,1,1,0,NULL,NULL),(1336,'Spaghetti',NULL,18.63,'100000000065',100,'Pantry','Pasta',NULL,'Heinz','Spaghetti','See package',NULL,NULL,5,2,'Pantry',17.1,203,334,0.9,5.2,4.6,8.7,4.5,105,1,1,0,1,0,NULL,NULL),(1337,'Penne',NULL,14.26,'100000000066',100,'Pantry','Pasta',NULL,'Heinz','Penne','See package',NULL,NULL,2,8,'Pantry',11.1,678,269,15.7,23.2,6.1,33.1,2.8,6,1,1,0,1,0,NULL,NULL),(1338,'Macaroni',NULL,16.72,'100000000067',100,'Pantry','Pasta',NULL,'American Garden','Macaroni','See package',NULL,NULL,10,5,'Pantry',3,586,261,24,5.3,6.1,2,5.8,115,1,1,0,1,0,NULL,NULL),(1339,'Olive Oil',NULL,2.4,'100000000068',100,'Pantry','Oil',NULL,'Knorr','Olive Oil','See package',NULL,NULL,6,7,'Pantry',11.4,261,123,0.2,27.3,2.8,56.7,2.6,18,1,1,1,1,0,NULL,NULL),(1340,'Sunflower Oil',NULL,13,'100000000069',100,'Pantry','Oil',NULL,'Heinz','Sunflower Oil','See package',NULL,NULL,7,1,'Pantry',13.4,559,478,22.8,17.5,3.1,31.1,8.2,21,1,1,1,1,0,NULL,NULL),(1341,'Soy Sauce',NULL,19.95,'100000000070',100,'Pantry','Sauce',NULL,'American Garden','Soy Sauce','See package',NULL,NULL,6,4,'Pantry',12.9,275,430,5.7,27.1,8.5,35.6,1.6,57,1,1,1,1,0,NULL,NULL),(1342,'Tomato Sauce',NULL,3.42,'100000000071',100,'Pantry','Sauce',NULL,'Barilla','Tomato Sauce','See package',NULL,NULL,9,8,'Pantry',1.7,232,396,0.1,6.6,0.1,35.6,3.3,76,1,1,1,1,0,NULL,NULL),(1343,'Ketchup',NULL,12.36,'100000000072',100,'Pantry','Sauce',NULL,'Knorr','Ketchup','See package',NULL,NULL,5,5,'Pantry',12.5,440,320,2.5,27.2,3.4,41.7,7.2,24,1,1,1,1,0,NULL,NULL),(1344,'Mayonnaise',NULL,13.92,'100000000073',100,'Pantry','Sauce',NULL,'American Garden','Mayonnaise','See package',NULL,NULL,2,8,'Pantry',17,373,326,23.1,1.7,6.3,54.7,9.6,61,1,1,1,1,0,NULL,NULL),(1345,'Flour',NULL,11.77,'100000000074',100,'Pantry','Other',NULL,'Knorr','Flour','See package',NULL,NULL,10,6,'Pantry',11.7,297,185,24.3,13,7.8,14,6.8,32,1,1,1,1,0,NULL,NULL),(1346,'Sugar',NULL,23.62,'100000000075',100,'Pantry','Other',NULL,'American Garden','Sugar','See package',NULL,NULL,7,9,'Pantry',17.1,622,63,18.2,9.7,1.1,12.4,6.9,98,1,1,1,1,0,NULL,NULL),(1347,'Salt',NULL,3.4,'100000000076',100,'Pantry','Other',NULL,'American Garden','Salt','See package',NULL,NULL,4,8,'Pantry',11.7,15,229,11.8,21.8,5.1,41.7,7.5,111,1,1,1,1,0,NULL,NULL),(1348,'Honey',NULL,7.16,'100000000077',100,'Pantry','Other',NULL,'American Garden','Honey','See package',NULL,NULL,3,7,'Pantry',14.7,27,380,8.9,26.4,1.8,26,6.1,53,1,1,1,1,0,NULL,NULL),(1349,'Oats',NULL,7.91,'100000000078',100,'Pantry','Other',NULL,'Heinz','Oats','See package',NULL,NULL,3,2,'Pantry',8.5,661,494,15.8,22.3,8.7,41.5,3,22,1,1,1,1,0,NULL,NULL),(1350,'Lentils',NULL,7.99,'100000000079',100,'Pantry','Other',NULL,'Barilla','Lentils','See package',NULL,NULL,5,9,'Pantry',8.8,258,422,27,13.9,6,8.7,1,84,1,1,1,1,0,NULL,NULL),(1351,'Beans',NULL,9.07,'100000000080',100,'Pantry','Other',NULL,'American Garden','Beans','See package',NULL,NULL,5,8,'Pantry',20,229,292,9.2,0.5,9.9,7.8,4.7,79,1,1,1,1,0,NULL,NULL),(1352,'Dark Chocolate',NULL,23.19,'100000000081',100,'Snacks','Chocolate',NULL,'Pringles','Dark Chocolate','See package',NULL,NULL,7,4,'Snacks',1.9,364,335,4.7,12.6,0.2,10.1,3.5,21,0,1,1,1,0,NULL,NULL),(1353,'Milk Chocolate',NULL,11.56,'100000000082',100,'Snacks','Chocolate',NULL,'Cadbury','Milk Chocolate','See package',NULL,NULL,8,8,'Snacks',17.4,501,360,21.6,20.5,8.6,21.9,8,96,0,1,1,1,0,NULL,NULL),(1354,'KitKat',NULL,7.42,'100000000083',100,'Snacks','Chocolate',NULL,'Nestlé','KitKat','See package',NULL,NULL,9,6,'Snacks',10.5,288,207,28,15.2,3.6,10.3,3.3,29,0,1,1,1,0,NULL,NULL),(1355,'Snickers',NULL,17.98,'100000000084',100,'Snacks','Chocolate',NULL,'Cadbury','Snickers','See package',NULL,NULL,3,6,'Snacks',8.6,466,111,21.3,18.5,6,33.5,0.4,95,0,1,1,1,0,NULL,NULL),(1356,'Twix',NULL,2.62,'100000000085',100,'Snacks','Chocolate',NULL,'Nestlé','Twix','See package',NULL,NULL,4,7,'Snacks',11.8,31,386,0.8,8,2.8,2.9,0,64,0,1,1,1,0,NULL,NULL),(1357,'Mixed Nuts',NULL,20.56,'100000000086',100,'Snacks','Nuts',NULL,'Lay\'s','Mixed Nuts','See package',NULL,NULL,9,4,'Snacks',6.5,633,225,13.7,4.8,8.7,47.4,4.9,63,0,1,1,1,0,NULL,NULL),(1358,'Almonds',NULL,21.09,'100000000087',100,'Snacks','Nuts',NULL,'Lay\'s','Almonds','See package',NULL,NULL,4,8,'Snacks',12.3,586,406,27,21.2,8,49.3,0.8,28,0,1,1,1,0,NULL,NULL),(1359,'Cashews',NULL,22.01,'100000000088',100,'Snacks','Nuts',NULL,'Cadbury','Cashews','See package',NULL,NULL,9,4,'Snacks',2.3,643,485,16.6,4.8,8.3,30.6,0.7,58,0,1,1,1,0,NULL,NULL),(1360,'Pistachios',NULL,19.56,'100000000089',100,'Snacks','Nuts',NULL,'Nestlé','Pistachios','See package',NULL,NULL,9,1,'Snacks',13.8,373,408,1.4,16.2,8.3,56.8,5,95,0,1,1,1,0,NULL,NULL),(1361,'Peanuts',NULL,11.13,'100000000090',100,'Snacks','Nuts',NULL,'Lay\'s','Peanuts','See package',NULL,NULL,3,6,'Snacks',17.7,66,360,23.8,14.5,7.4,37,4.6,11,0,1,1,1,0,NULL,NULL),(1362,'Pringles',NULL,24.62,'100000000091',100,'Snacks','Chips',NULL,'Nestlé','Pringles','See package',NULL,NULL,6,2,'Snacks',0.3,672,253,0.2,8.1,4.8,10,0.4,89,0,1,1,1,0,NULL,NULL),(1363,'Lay\'s',NULL,14.2,'100000000092',100,'Snacks','Chips',NULL,'Lay\'s','Lay\'s','See package',NULL,NULL,7,1,'Snacks',15.8,646,307,28.9,14,9.6,3.1,2.9,107,0,1,1,1,0,NULL,NULL),(1364,'Doritos',NULL,19.42,'100000000093',100,'Snacks','Chips',NULL,'Lay\'s','Doritos','See package',NULL,NULL,6,8,'Snacks',16.8,611,139,9.5,28.5,2.8,24,4.2,52,0,1,1,1,0,NULL,NULL),(1365,'Popcorn',NULL,2.94,'100000000094',100,'Snacks','Chips',NULL,'Cadbury','Popcorn','See package',NULL,NULL,6,5,'Snacks',12.7,466,252,29.1,10.1,8.8,9.4,9.8,95,0,1,1,1,0,NULL,NULL),(1366,'Mineral Water',NULL,18.12,'100000000095',100,'Beverages','Water',NULL,'Pepsi','Mineral Water','See package',NULL,NULL,9,10,'Beverages',15.3,291,369,4.1,5.9,8.5,18.1,8.6,59,1,1,1,1,0,NULL,NULL),(1367,'Sparkling Water',NULL,4.85,'100000000096',100,'Beverages','Water',NULL,'Lipton','Sparkling Water','See package',NULL,NULL,4,6,'Beverages',16,688,50,5.2,2.8,3.4,26.2,9.6,23,1,1,1,1,0,NULL,NULL),(1368,'Coconut Water',NULL,11.89,'100000000097',100,'Beverages','Water',NULL,'Coca-Cola','Coconut Water','See package',NULL,NULL,2,10,'Beverages',11.3,97,480,16.9,2.2,3.7,48.2,5.8,45,1,1,1,1,0,NULL,NULL),(1369,'Orange Juice',NULL,16.52,'100000000098',100,'Beverages','Juice',NULL,'Pepsi','Orange Juice','See package',NULL,NULL,7,10,'Beverages',12.1,316,279,21.8,22.2,6.6,14.3,7.1,47,1,1,1,1,0,NULL,NULL),(1370,'Apple Juice',NULL,5.15,'100000000099',100,'Beverages','Juice',NULL,'Tropicana','Apple Juice','See package',NULL,NULL,4,4,'Beverages',13.2,19,128,10,13.2,0.5,46.6,3,77,1,1,1,1,0,NULL,NULL),(1371,'Mango Juice',NULL,12.16,'100000000100',100,'Beverages','Juice',NULL,'Tropicana','Mango Juice','See package',NULL,NULL,2,8,'Beverages',14.9,348,216,2.5,16.4,10,47.6,2.8,3,1,1,1,1,0,NULL,NULL),(1372,'Green Tea',NULL,7.17,'100000000101',100,'Beverages','Tea',NULL,'Tropicana','Green Tea','See package',NULL,NULL,6,9,'Beverages',7.4,434,438,5.1,18.3,6.4,14.6,4.8,58,1,1,1,1,0,NULL,NULL),(1373,'Black Tea',NULL,19.69,'100000000102',100,'Beverages','Tea',NULL,'Lipton','Black Tea','See package',NULL,NULL,10,2,'Beverages',14,231,205,6,28.4,4.1,42,6.8,20,1,1,1,1,0,NULL,NULL),(1374,'Ground Coffee',NULL,12.13,'100000000103',100,'Beverages','Coffee',NULL,'Coca-Cola','Ground Coffee','See package',NULL,NULL,9,5,'Beverages',8.6,295,302,25.3,5.4,1.7,39.8,6,86,1,1,1,1,0,NULL,NULL),(1375,'Cola',NULL,11.44,'100000000104',100,'Beverages','Soft Drink',NULL,'Lipton','Cola','See package',NULL,NULL,10,7,'Beverages',2,429,414,7.7,0.1,8.8,55.7,1,116,1,1,1,1,0,NULL,NULL),(1376,'Diet Cola',NULL,22.08,'100000000105',100,'Beverages','Soft Drink',NULL,'Coca-Cola','Diet Cola','See package',NULL,NULL,10,4,'Beverages',6.6,416,300,13.9,8.4,8,3,7.6,117,1,1,1,1,0,NULL,NULL),(1377,'Energy Drink',NULL,14.16,'100000000106',100,'Beverages','Soft Drink',NULL,'Coca-Cola','Energy Drink','See package',NULL,NULL,9,9,'Beverages',2.3,144,406,23.1,9.8,0.7,47.8,9.8,96,1,1,1,1,0,NULL,NULL),(1378,'Whole Milk 1L',NULL,17.5,'100000000107',100,'Dairy','Milk',NULL,'Arla','Whole Milk 1L','See package','Milk',NULL,5,10,'Dairy',7.7,637,194,15.7,9.8,9.3,29.7,7.1,24,0,1,1,0,0,NULL,NULL),(1379,'Low Fat Milk 1L',NULL,5.38,'100000000108',100,'Dairy','Milk',NULL,'Arla','Low Fat Milk 1L','See package','Milk',NULL,2,3,'Dairy',5.6,608,443,27.6,15,3.7,48.2,1.5,92,0,1,1,0,0,NULL,NULL),(1380,'Skim Milk 1L',NULL,4.25,'100000000109',100,'Dairy','Milk',NULL,'Arla','Skim Milk 1L','See package','Milk',NULL,2,6,'Dairy',3.3,545,57,11.9,7.3,4.1,14.9,7.4,10,0,1,1,0,0,NULL,NULL),(1381,'Lactose Free Milk',NULL,23.2,'100000000110',100,'Dairy','Milk',NULL,'Arla','Lactose Free Milk','See package','Milk',NULL,6,3,'Dairy',13.7,519,49,5.3,4.4,5.8,25.2,3.6,23,0,1,1,0,0,NULL,NULL),(1382,'Almond Milk',NULL,20.71,'100000000111',100,'Dairy','Milk',NULL,'Alpro','Almond Milk','See package','Milk',NULL,8,4,'Dairy',10.2,182,193,24.2,21,4,59.2,9.1,113,0,1,1,0,0,NULL,NULL),(1383,'Oat Milk',NULL,22.74,'100000000112',100,'Dairy','Milk',NULL,'Alpro','Oat Milk','See package','Milk',NULL,8,3,'Dairy',16.4,465,94,13.9,2.1,3.6,53.6,3.6,17,0,1,1,0,0,NULL,NULL),(1384,'Soy Milk',NULL,20.8,'100000000113',100,'Dairy','Milk',NULL,'Arla','Soy Milk','See package','Milk',NULL,3,10,'Dairy',3.9,132,133,18.2,26.4,8.8,20.7,1.8,65,0,1,1,0,0,NULL,NULL),(1385,'Greek Yogurt',NULL,24.54,'100000000114',100,'Dairy','Yogurt',NULL,'President','Greek Yogurt','See package','Milk',NULL,10,4,'Dairy',12.6,590,466,20.1,17.6,9.1,55.6,2.7,45,0,1,1,0,0,NULL,NULL),(1386,'Strawberry Yogurt',NULL,2.18,'100000000115',100,'Dairy','Yogurt',NULL,'Arla','Strawberry Yogurt','See package','Milk',NULL,8,2,'Dairy',16.1,384,202,5.8,29.7,2.5,0.8,0.9,103,0,1,1,0,0,NULL,NULL),(1387,'Vanilla Yogurt',NULL,13.21,'100000000116',100,'Dairy','Yogurt',NULL,'Alpro','Vanilla Yogurt','See package','Milk',NULL,4,10,'Dairy',6.8,558,103,11,0.8,6.3,23.2,10,4,0,1,1,0,0,NULL,NULL),(1388,'Labneh',NULL,5.53,'100000000117',100,'Dairy','Yogurt',NULL,'President','Labneh','See package','Milk',NULL,7,6,'Dairy',19.5,56,66,0.3,6.2,8.7,34.5,9.7,14,0,1,1,0,0,NULL,NULL),(1389,'Cheddar Cheese',NULL,24.94,'100000000118',100,'Dairy','Cheese',NULL,'Alpro','Cheddar Cheese','See package','Milk',NULL,2,10,'Dairy',9.3,543,308,20,2.5,7.2,46.7,2.2,85,0,1,1,0,0,NULL,NULL),(1390,'Mozzarella',NULL,7.12,'100000000119',100,'Dairy','Cheese',NULL,'Lurpak','Mozzarella','See package','Milk',NULL,9,2,'Dairy',19.5,638,196,13.1,24,8.4,25.9,8.6,94,0,1,1,0,0,NULL,NULL),(1391,'Cream Cheese',NULL,13.68,'100000000120',100,'Dairy','Cheese',NULL,'President','Cream Cheese','See package','Milk',NULL,8,7,'Dairy',0.7,78,233,27.5,9.7,8,5,3,17,0,1,1,0,0,NULL,NULL),(1392,'Feta',NULL,19.88,'100000000121',100,'Dairy','Cheese',NULL,'President','Feta','See package','Milk',NULL,7,6,'Dairy',5.9,8,214,20.4,20.1,3.4,11.7,1.5,101,0,1,1,0,0,NULL,NULL),(1393,'Parmesan',NULL,13.45,'100000000122',100,'Dairy','Cheese',NULL,'Lurpak','Parmesan','See package','Milk',NULL,6,10,'Dairy',7.3,378,184,3.9,13.2,5.1,46.8,5.3,24,0,1,1,0,0,NULL,NULL),(1394,'Salted Butter',NULL,7.72,'100000000123',100,'Dairy','Butter',NULL,'President','Salted Butter','See package','Milk',NULL,1,2,'Dairy',14.1,367,431,29.8,4.4,3,19.8,9.6,26,0,1,1,0,0,NULL,NULL),(1395,'Unsalted Butter',NULL,14.75,'100000000124',100,'Dairy','Butter',NULL,'Arla','Unsalted Butter','See package','Milk',NULL,10,3,'Dairy',15.8,363,294,4,5.3,8,58.3,4.7,29,0,1,1,0,0,NULL,NULL),(1396,'White Bread',NULL,20.28,'100000000125',100,'Bakery','Bread',NULL,'Golden Bakery','White Bread','See package',NULL,NULL,1,3,'Bakery',13.3,528,401,1.1,11,7.8,39.2,8.5,99,0,1,0,1,0,NULL,NULL),(1397,'Whole Wheat Bread',NULL,19.78,'100000000126',100,'Bakery','Bread',NULL,'Golden Bakery','Whole Wheat Bread','See package',NULL,NULL,5,4,'Bakery',18.2,220,242,1.9,9.4,5.9,57.9,5.6,9,0,1,0,1,0,NULL,NULL),(1398,'Brown Bread',NULL,5.71,'100000000127',100,'Bakery','Bread',NULL,'Wonder','Brown Bread','See package',NULL,NULL,4,2,'Bakery',1.2,490,63,6.3,3,7.9,57.3,9.4,100,0,1,0,1,0,NULL,NULL),(1399,'Toast Bread',NULL,14.79,'100000000128',100,'Bakery','Bread',NULL,'Golden Bakery','Toast Bread','See package',NULL,NULL,5,4,'Bakery',12.5,480,127,2.8,11.2,4.4,6.4,1.8,38,0,1,0,1,0,NULL,NULL),(1400,'Pita Bread',NULL,5.12,'100000000129',100,'Bakery','Bread',NULL,'Golden Bakery','Pita Bread','See package',NULL,NULL,4,9,'Bakery',19.2,215,179,13.1,25.3,4.7,7.8,5.9,61,0,1,0,1,0,NULL,NULL),(1401,'Sourdough',NULL,13,'100000000130',100,'Bakery','Bread',NULL,'Wonder','Sourdough','See package',NULL,NULL,5,8,'Bakery',14.5,60,23,9.3,19.5,1.8,31.7,5.7,120,0,1,0,1,0,NULL,NULL),(1402,'Burger Buns',NULL,8.6,'100000000131',100,'Bakery','Bread',NULL,'Golden Bakery','Burger Buns','See package',NULL,NULL,3,3,'Bakery',3.2,404,189,20.5,14.1,9.8,23.6,7.6,114,0,1,0,1,0,NULL,NULL),(1403,'Hot Dog Buns',NULL,23.52,'100000000132',100,'Bakery','Bread',NULL,'Wonder','Hot Dog Buns','See package',NULL,NULL,4,8,'Bakery',2.2,674,276,20.6,12.2,1.5,16.7,0.8,63,0,1,0,1,0,NULL,NULL),(1404,'Croissant',NULL,10.7,'100000000133',100,'Bakery','Pastry',NULL,'Golden Bakery','Croissant','See package',NULL,NULL,3,7,'Bakery',18.4,364,156,28.7,8.3,3.3,53.1,9.6,66,0,1,0,1,0,NULL,NULL),(1405,'Donut',NULL,22.85,'100000000134',100,'Bakery','Pastry',NULL,'Wonder','Donut','See package',NULL,NULL,7,8,'Bakery',12.1,566,51,5.6,29.5,6.2,2.6,3,101,0,1,0,1,0,NULL,NULL),(1406,'Muffin',NULL,21.3,'100000000135',100,'Bakery','Pastry',NULL,'Wonder','Muffin','See package',NULL,NULL,3,10,'Bakery',10.8,220,130,21.3,14.9,2.2,6.5,6.9,59,0,1,0,1,0,NULL,NULL),(1407,'Bagel',NULL,7.69,'100000000136',100,'Bakery','Pastry',NULL,'Wonder','Bagel','See package',NULL,NULL,6,3,'Bakery',10.5,409,454,18.6,16.2,2.5,54.7,6.7,101,0,1,0,1,0,NULL,NULL),(1408,'Apple',NULL,14.38,'100000000137',100,'Produce','Fruit',NULL,'FreshFarm','Apple','See package',NULL,NULL,3,10,'Produce',8.8,635,298,7.1,1.1,4,39.7,6.4,34,1,1,1,1,0,NULL,NULL),(1409,'Banana',NULL,7.33,'100000000138',100,'Produce','Fruit',NULL,'FreshFarm','Banana','See package',NULL,NULL,10,8,'Produce',12.4,593,283,29.6,24.6,1.5,41.1,3.9,75,1,1,1,1,0,NULL,NULL),(1410,'Orange',NULL,22.96,'100000000139',100,'Produce','Fruit',NULL,'FreshFarm','Orange','See package',NULL,NULL,8,4,'Produce',4.8,304,361,5,22.4,8.3,56.6,6.8,17,1,1,1,1,0,NULL,NULL),(1411,'Pear',NULL,5.21,'100000000140',100,'Produce','Fruit',NULL,'FreshFarm','Pear','See package',NULL,NULL,9,5,'Produce',9.3,402,450,20.7,27.3,0.1,48,5,92,1,1,1,1,0,NULL,NULL),(1412,'Grapes',NULL,16.98,'100000000141',100,'Produce','Fruit',NULL,'FreshFarm','Grapes','See package',NULL,NULL,2,6,'Produce',18.4,285,128,9.4,15,0.2,50.4,6.1,66,1,1,1,1,0,NULL,NULL),(1413,'Mango',NULL,7.12,'100000000142',100,'Produce','Fruit',NULL,'FreshFarm','Mango','See package',NULL,NULL,3,6,'Produce',1,406,278,6.3,18.3,9.5,12.7,9.9,16,1,1,1,1,0,NULL,NULL),(1414,'Kiwi',NULL,3.86,'100000000143',100,'Produce','Fruit',NULL,'FreshFarm','Kiwi','See package',NULL,NULL,9,4,'Produce',0.6,582,193,6.8,14.7,3,20.1,5.1,79,1,1,1,1,0,NULL,NULL),(1415,'Pineapple',NULL,5.94,'100000000144',100,'Produce','Fruit',NULL,'FreshFarm','Pineapple','See package',NULL,NULL,1,7,'Produce',11.3,515,186,18.7,12.9,5.3,33.3,0.3,58,1,1,1,1,0,NULL,NULL),(1416,'Watermelon',NULL,22.64,'100000000145',100,'Produce','Fruit',NULL,'FreshFarm','Watermelon','See package',NULL,NULL,9,7,'Produce',13.7,385,305,28.9,3.2,3.3,12.5,8.5,16,1,1,1,1,0,NULL,NULL),(1417,'Lemon',NULL,21,'100000000146',100,'Produce','Fruit',NULL,'FreshFarm','Lemon','See package',NULL,NULL,2,3,'Produce',8.3,65,278,2.8,1.9,9.9,16.2,0.9,62,1,1,1,1,0,NULL,NULL),(1418,'Avocado',NULL,22.41,'100000000147',100,'Produce','Fruit',NULL,'FreshFarm','Avocado','See package',NULL,NULL,7,10,'Produce',12.3,496,282,25.1,23.6,4.3,1,1,26,1,1,1,1,0,NULL,NULL),(1419,'Tomato',NULL,23.38,'100000000148',100,'Produce','Vegetable',NULL,'FreshFarm','Tomato','See package',NULL,NULL,6,3,'Produce',14.3,562,222,17.4,5.9,2.4,29.6,9.1,115,1,1,1,1,0,NULL,NULL),(1420,'Potato',NULL,16.54,'100000000149',100,'Produce','Vegetable',NULL,'FreshFarm','Potato','See package',NULL,NULL,8,3,'Produce',18.6,137,230,27.1,4.4,9.9,24.2,3.1,91,1,1,1,1,0,NULL,NULL),(1421,'Onion',NULL,21.44,'100000000150',100,'Produce','Vegetable',NULL,'FreshFarm','Onion','See package',NULL,NULL,9,1,'Produce',7.5,127,38,27.9,24.3,2.3,21.2,5.8,84,1,1,1,1,0,NULL,NULL),(1422,'Garlic',NULL,17.06,'100000000151',100,'Produce','Vegetable',NULL,'FreshFarm','Garlic','See package',NULL,NULL,3,6,'Produce',5.7,676,493,2.9,23.7,6,37.9,1.3,68,1,1,1,1,0,NULL,NULL),(1423,'Carrot',NULL,16.72,'100000000152',100,'Produce','Vegetable',NULL,'FreshFarm','Carrot','See package',NULL,NULL,7,5,'Produce',4.3,130,60,17.6,29.1,2.5,31.8,5.3,14,1,1,1,1,0,NULL,NULL),(1424,'Cucumber',NULL,23.32,'100000000153',100,'Produce','Vegetable',NULL,'FreshFarm','Cucumber','See package',NULL,NULL,2,7,'Produce',9.7,567,317,28.1,1.8,0.1,13,1.6,45,1,1,1,1,0,NULL,NULL),(1425,'Broccoli',NULL,4.75,'100000000154',100,'Produce','Vegetable',NULL,'FreshFarm','Broccoli','See package',NULL,NULL,5,8,'Produce',13.6,416,116,25.6,17.1,1.9,19.6,1.9,39,1,1,1,1,0,NULL,NULL),(1426,'Spinach',NULL,22.31,'100000000155',100,'Produce','Vegetable',NULL,'FreshFarm','Spinach','See package',NULL,NULL,7,4,'Produce',5.7,328,494,28.1,1,4.6,57.9,2.1,46,1,1,1,1,0,NULL,NULL),(1427,'Lettuce',NULL,7.35,'100000000156',100,'Produce','Vegetable',NULL,'FreshFarm','Lettuce','See package',NULL,NULL,4,7,'Produce',12.1,404,490,21.1,22.6,4.7,4.5,2,94,1,1,1,1,0,NULL,NULL),(1428,'Bell Pepper',NULL,20.81,'100000000157',100,'Produce','Vegetable',NULL,'FreshFarm','Bell Pepper','See package',NULL,NULL,8,5,'Produce',18.4,612,484,20.9,0.9,2.1,45.1,1.4,9,1,1,1,1,0,NULL,NULL),(1429,'Chicken Breast',NULL,24.96,'100000000158',100,'Meat','Poultry',NULL,'Tyson','Chicken Breast','See package',NULL,NULL,1,3,'Meat',11.6,388,465,24.9,28.1,8.7,4,2.5,1,0,0,1,1,0,NULL,NULL),(1430,'Chicken Thigh',NULL,23.65,'100000000159',100,'Meat','Poultry',NULL,'Tyson','Chicken Thigh','See package',NULL,NULL,8,4,'Meat',16.6,147,299,12.2,24.4,4.9,44.7,4.1,31,0,0,1,1,0,NULL,NULL),(1431,'Chicken Wings',NULL,3.94,'100000000160',100,'Meat','Poultry',NULL,'Tyson','Chicken Wings','See package',NULL,NULL,5,2,'Meat',9.5,168,48,14.2,24.9,0.3,53.7,4.3,111,0,0,1,1,0,NULL,NULL),(1432,'Ground Chicken',NULL,5.01,'100000000161',100,'Meat','Poultry',NULL,'FreshFarm','Ground Chicken','See package',NULL,NULL,9,9,'Meat',15.7,381,127,23.1,21.8,8.9,13.3,6,16,0,0,1,1,0,NULL,NULL),(1433,'Beef Steak',NULL,17.23,'100000000162',100,'Meat','Beef',NULL,'Tyson','Beef Steak','See package',NULL,NULL,3,10,'Meat',17.5,252,39,15,8.7,6.2,16.7,2.6,115,0,0,1,1,0,NULL,NULL),(1434,'Ground Beef',NULL,17.51,'100000000163',100,'Meat','Beef',NULL,'FreshFarm','Ground Beef','See package',NULL,NULL,1,2,'Meat',9.9,232,283,22.2,6.4,2.9,37.2,4,62,0,0,1,1,0,NULL,NULL),(1435,'Beef Burger',NULL,18.87,'100000000164',100,'Meat','Beef',NULL,'FreshFarm','Beef Burger','See package',NULL,NULL,8,2,'Meat',18.9,312,151,26.9,17.2,0.4,55.4,2.4,94,0,0,1,1,0,NULL,NULL),(1436,'Salmon',NULL,2.21,'100000000165',100,'Meat','Seafood',NULL,'FreshFarm','Salmon','See package',NULL,NULL,6,5,'Meat',0.9,250,459,13.4,28,8.2,10.1,8.2,48,0,0,1,1,0,NULL,NULL),(1437,'Tuna',NULL,13.23,'100000000166',100,'Meat','Seafood',NULL,'FreshFarm','Tuna','See package',NULL,NULL,4,9,'Meat',3.6,611,284,11.3,26,2.4,8.9,3,102,0,0,1,1,0,NULL,NULL),(1438,'Shrimp',NULL,11.55,'100000000167',100,'Meat','Seafood',NULL,'Tyson','Shrimp','See package',NULL,NULL,6,4,'Meat',6.8,387,384,18.2,13.9,9.9,41.6,1.9,50,0,0,1,1,0,NULL,NULL),(1439,'White Rice',NULL,12.82,'100000000168',100,'Pantry','Rice',NULL,'Heinz','White Rice','See package',NULL,NULL,6,2,'Pantry',4.1,678,67,15.1,9.8,1.7,33.8,8.4,101,1,1,1,1,0,NULL,NULL),(1440,'Brown Rice',NULL,20.57,'100000000169',100,'Pantry','Rice',NULL,'Barilla','Brown Rice','See package',NULL,NULL,10,2,'Pantry',17.6,319,464,2.5,3.5,2,7.6,4.2,27,1,1,1,1,0,NULL,NULL),(1441,'Basmati Rice',NULL,7.31,'100000000170',100,'Pantry','Rice',NULL,'Knorr','Basmati Rice','See package',NULL,NULL,9,6,'Pantry',4.8,4,478,6.9,11.4,1.7,56.9,8,83,1,1,1,1,0,NULL,NULL),(1442,'Spaghetti',NULL,16.11,'100000000171',100,'Pantry','Pasta',NULL,'American Garden','Spaghetti','See package',NULL,NULL,6,4,'Pantry',13.3,210,436,17.7,19.6,5.4,9.2,4.2,91,1,1,0,1,0,NULL,NULL),(1443,'Penne',NULL,16.86,'100000000172',100,'Pantry','Pasta',NULL,'American Garden','Penne','See package',NULL,NULL,1,5,'Pantry',16.8,596,222,24,24.5,4.5,29.4,5.9,91,1,1,0,1,0,NULL,NULL),(1444,'Macaroni',NULL,24.19,'100000000173',100,'Pantry','Pasta',NULL,'Barilla','Macaroni','See package',NULL,NULL,10,8,'Pantry',17.7,171,473,12,5.2,3.3,53.8,1.7,33,1,1,0,1,0,NULL,NULL),(1445,'Olive Oil',NULL,5.19,'100000000174',100,'Pantry','Oil',NULL,'Knorr','Olive Oil','See package',NULL,NULL,8,9,'Pantry',18.3,539,316,19.7,23.3,2.4,41.6,9.9,107,1,1,1,1,0,NULL,NULL),(1446,'Sunflower Oil',NULL,12.01,'100000000175',100,'Pantry','Oil',NULL,'Barilla','Sunflower Oil','See package',NULL,NULL,3,2,'Pantry',17.9,269,291,19,23.7,5.2,11.7,5.4,7,1,1,1,1,0,NULL,NULL),(1447,'Soy Sauce',NULL,13.17,'100000000176',100,'Pantry','Sauce',NULL,'Heinz','Soy Sauce','See package',NULL,NULL,8,6,'Pantry',12.3,145,250,29.7,12.5,6.7,49.3,2.9,86,1,1,1,1,0,NULL,NULL),(1448,'Tomato Sauce',NULL,2.07,'100000000177',100,'Pantry','Sauce',NULL,'Knorr','Tomato Sauce','See package',NULL,NULL,3,9,'Pantry',8.3,495,417,25,0.8,0.9,38.6,0.7,53,1,1,1,1,0,NULL,NULL),(1449,'Ketchup',NULL,11.21,'100000000178',100,'Pantry','Sauce',NULL,'Barilla','Ketchup','See package',NULL,NULL,6,9,'Pantry',19.6,339,322,2.5,20.6,4.8,26.2,8.1,120,1,1,1,1,0,NULL,NULL),(1450,'Mayonnaise',NULL,16.36,'100000000179',100,'Pantry','Sauce',NULL,'American Garden','Mayonnaise','See package',NULL,NULL,6,9,'Pantry',3.6,69,266,17.9,27.6,1.3,1,4.8,112,1,1,1,1,0,NULL,NULL),(1451,'Flour',NULL,14.94,'100000000180',100,'Pantry','Other',NULL,'Knorr','Flour','See package',NULL,NULL,5,2,'Pantry',19.5,98,168,8.5,12.2,0.6,31.8,7.2,117,1,1,1,1,0,NULL,NULL),(1452,'Sugar',NULL,11.2,'100000000181',100,'Pantry','Other',NULL,'Barilla','Sugar','See package',NULL,NULL,1,4,'Pantry',7.2,685,353,19.8,1.6,8.8,50.5,2.9,105,1,1,1,1,0,NULL,NULL),(1453,'Salt',NULL,14.77,'100000000182',100,'Pantry','Other',NULL,'Barilla','Salt','See package',NULL,NULL,7,8,'Pantry',7.1,600,360,22.5,6.3,9.6,58.1,0.2,21,1,1,1,1,0,NULL,NULL),(1454,'Honey',NULL,3.97,'100000000183',100,'Pantry','Other',NULL,'Barilla','Honey','See package',NULL,NULL,8,4,'Pantry',7.6,284,123,20,11.7,3.2,48.9,4.5,48,1,1,1,1,0,NULL,NULL),(1455,'Oats',NULL,19.72,'100000000184',100,'Pantry','Other',NULL,'Heinz','Oats','See package',NULL,NULL,4,10,'Pantry',15.3,379,420,7.6,6.7,6.2,33.4,3.4,76,1,1,1,1,0,NULL,NULL),(1456,'Lentils',NULL,18.33,'100000000185',100,'Pantry','Other',NULL,'American Garden','Lentils','See package',NULL,NULL,9,4,'Pantry',10.4,429,84,10.2,21.3,9.3,53,8.4,37,1,1,1,1,0,NULL,NULL),(1457,'Beans',NULL,20.36,'100000000186',100,'Pantry','Other',NULL,'Barilla','Beans','See package',NULL,NULL,6,3,'Pantry',5.1,502,29,3.1,16.5,4.4,53.9,1.9,101,1,1,1,1,0,NULL,NULL),(1458,'Dark Chocolate',NULL,2.14,'100000000187',100,'Snacks','Chocolate',NULL,'Pringles','Dark Chocolate','See package',NULL,NULL,2,8,'Snacks',16.1,44,263,9.7,11.3,5,33,1.7,105,0,1,1,1,0,NULL,NULL),(1459,'Milk Chocolate',NULL,3.68,'100000000188',100,'Snacks','Chocolate',NULL,'Lay\'s','Milk Chocolate','See package',NULL,NULL,1,5,'Snacks',10.5,23,121,17.9,10.7,0.1,48,5.6,108,0,1,1,1,0,NULL,NULL),(1460,'KitKat',NULL,17.79,'100000000189',100,'Snacks','Chocolate',NULL,'Cadbury','KitKat','See package',NULL,NULL,7,6,'Snacks',2.6,613,496,15,2.8,6.9,20,8,32,0,1,1,1,0,NULL,NULL),(1461,'Snickers',NULL,21.44,'100000000190',100,'Snacks','Chocolate',NULL,'Pringles','Snickers','See package',NULL,NULL,6,5,'Snacks',16.2,563,273,15.6,10.3,3.2,27.8,6.1,57,0,1,1,1,0,NULL,NULL),(1462,'Twix',NULL,10.82,'100000000191',100,'Snacks','Chocolate',NULL,'Cadbury','Twix','See package',NULL,NULL,9,3,'Snacks',3.9,51,442,26.9,22.2,6.3,54.6,6.9,65,0,1,1,1,0,NULL,NULL),(1463,'Mixed Nuts',NULL,22.55,'100000000192',100,'Snacks','Nuts',NULL,'Lay\'s','Mixed Nuts','See package',NULL,NULL,2,9,'Snacks',3.9,638,335,0.3,7.5,4.7,59,8.7,5,0,1,1,1,0,NULL,NULL),(1464,'Almonds',NULL,11.93,'100000000193',100,'Snacks','Nuts',NULL,'Cadbury','Almonds','See package',NULL,NULL,10,2,'Snacks',5.2,419,368,20.1,11.4,2.1,27.9,9.5,37,0,1,1,1,0,NULL,NULL),(1465,'Cashews',NULL,20.92,'100000000194',100,'Snacks','Nuts',NULL,'Cadbury','Cashews','See package',NULL,NULL,10,2,'Snacks',19.1,423,188,16.5,0.8,4.2,28.5,1.8,48,0,1,1,1,0,NULL,NULL),(1466,'Pistachios',NULL,24.02,'100000000195',100,'Snacks','Nuts',NULL,'Nestlé','Pistachios','See package',NULL,NULL,9,7,'Snacks',0.5,338,241,30,26.4,1,35.1,0.8,19,0,1,1,1,0,NULL,NULL),(1467,'Peanuts',NULL,19.08,'100000000196',100,'Snacks','Nuts',NULL,'Lay\'s','Peanuts','See package',NULL,NULL,1,10,'Snacks',3.7,196,430,18.1,2,9.2,30.3,0.3,119,0,1,1,1,0,NULL,NULL),(1468,'Pringles',NULL,6.86,'100000000197',100,'Snacks','Chips',NULL,'Lay\'s','Pringles','See package',NULL,NULL,1,10,'Snacks',16.3,156,299,5.2,18.4,2.9,27.7,5.7,114,0,1,1,1,0,NULL,NULL),(1469,'Lay\'s',NULL,24.92,'100000000198',100,'Snacks','Chips',NULL,'Cadbury','Lay\'s','See package',NULL,NULL,1,7,'Snacks',6.6,222,56,6,2.6,7.8,12.6,1.3,107,0,1,1,1,0,NULL,NULL),(1470,'Doritos',NULL,17.56,'100000000199',100,'Snacks','Chips',NULL,'Cadbury','Doritos','See package',NULL,NULL,8,4,'Snacks',2,475,346,10.9,0.3,0.9,20.3,2.6,68,0,1,1,1,0,NULL,NULL),(1471,'Popcorn',NULL,7.16,'100000000200',100,'Snacks','Chips',NULL,'Pringles','Popcorn','See package',NULL,NULL,8,8,'Snacks',6.5,456,305,11.5,28.9,1.8,43.3,4,24,0,1,1,1,0,NULL,NULL),(1472,'Mineral Water',NULL,7.05,'100000000201',100,'Beverages','Water',NULL,'Tropicana','Mineral Water','See package',NULL,NULL,2,8,'Beverages',9.1,425,204,11.2,18.6,3.6,39,8,50,1,1,1,1,0,NULL,NULL),(1473,'Sparkling Water',NULL,15.71,'100000000202',100,'Beverages','Water',NULL,'Coca-Cola','Sparkling Water','See package',NULL,NULL,10,2,'Beverages',3.4,368,117,16.5,22,5.2,6.4,2.5,53,1,1,1,1,0,NULL,NULL),(1474,'Coconut Water',NULL,16.13,'100000000203',100,'Beverages','Water',NULL,'Pepsi','Coconut Water','See package',NULL,NULL,5,10,'Beverages',15.4,370,103,26.7,21.1,4.9,16,3.8,86,1,1,1,1,0,NULL,NULL),(1475,'Orange Juice',NULL,3.29,'100000000204',100,'Beverages','Juice',NULL,'Nestlé','Orange Juice','See package',NULL,NULL,1,2,'Beverages',4,223,231,4.1,26,9.8,25,8.4,53,1,1,1,1,0,NULL,NULL),(1476,'Apple Juice',NULL,18.21,'100000000205',100,'Beverages','Juice',NULL,'Lipton','Apple Juice','See package',NULL,NULL,5,2,'Beverages',19.6,539,31,8.9,1.5,2.4,26.1,2,93,1,1,1,1,0,NULL,NULL),(1477,'Mango Juice',NULL,11.25,'100000000206',100,'Beverages','Juice',NULL,'Lipton','Mango Juice','See package',NULL,NULL,1,1,'Beverages',7.8,655,368,11.5,8.5,2.6,43.4,8,87,1,1,1,1,0,NULL,NULL),(1478,'Green Tea',NULL,6.12,'100000000207',100,'Beverages','Tea',NULL,'Pepsi','Green Tea','See package',NULL,NULL,7,1,'Beverages',2.1,591,51,12.7,1.2,3.4,3.1,3.4,86,1,1,1,1,0,NULL,NULL),(1479,'Black Tea',NULL,2.36,'100000000208',100,'Beverages','Tea',NULL,'Nestlé','Black Tea','See package',NULL,NULL,7,6,'Beverages',14,140,34,25.5,9.2,8.1,36.4,4.9,117,1,1,1,1,0,NULL,NULL),(1480,'Ground Coffee',NULL,24.48,'100000000209',100,'Beverages','Coffee',NULL,'Tropicana','Ground Coffee','See package',NULL,NULL,7,10,'Beverages',16,283,363,29.9,24.1,8.9,26.8,8.2,80,1,1,1,1,0,NULL,NULL),(1481,'Cola',NULL,5.88,'100000000210',100,'Beverages','Soft Drink',NULL,'Lipton','Cola','See package',NULL,NULL,8,10,'Beverages',17.5,371,37,13.9,7.5,0.2,28.8,3.2,57,1,1,1,1,0,NULL,NULL),(1482,'Diet Cola',NULL,4.62,'100000000211',100,'Beverages','Soft Drink',NULL,'Coca-Cola','Diet Cola','See package',NULL,NULL,5,5,'Beverages',5.6,379,349,28.1,14.1,6.2,52.4,0.6,41,1,1,1,1,0,NULL,NULL),(1483,'Energy Drink',NULL,22.93,'100000000212',100,'Beverages','Soft Drink',NULL,'Tropicana','Energy Drink','See package',NULL,NULL,9,10,'Beverages',0.3,251,42,17.2,11.2,1.4,45.3,1.6,43,1,1,1,1,0,NULL,NULL),(1484,'Whole Milk 1L',NULL,7.2,'100000000213',100,'Dairy','Milk',NULL,'Alpro','Whole Milk 1L','See package','Milk',NULL,10,10,'Dairy',14.8,550,191,18.3,13.9,2.3,4.6,3.7,19,0,1,1,0,0,NULL,NULL),(1485,'Low Fat Milk 1L',NULL,21.09,'100000000214',100,'Dairy','Milk',NULL,'FreshFarm','Low Fat Milk 1L','See package','Milk',NULL,9,9,'Dairy',17.4,242,39,3.7,25.4,8.5,46.6,9.2,67,0,1,1,0,0,NULL,NULL),(1486,'Skim Milk 1L',NULL,8.93,'100000000215',100,'Dairy','Milk',NULL,'FreshFarm','Skim Milk 1L','See package','Milk',NULL,9,7,'Dairy',9.9,51,399,6.1,11.1,9.5,20,9.2,24,0,1,1,0,0,NULL,NULL),(1487,'Lactose Free Milk',NULL,14.72,'100000000216',100,'Dairy','Milk',NULL,'Lurpak','Lactose Free Milk','See package','Milk',NULL,6,4,'Dairy',9.4,102,58,21.4,11.9,1.6,12.2,0.6,92,0,1,1,0,0,NULL,NULL),(1488,'Almond Milk',NULL,16.37,'100000000217',100,'Dairy','Milk',NULL,'FreshFarm','Almond Milk','See package','Milk',NULL,3,9,'Dairy',13.3,125,195,23.1,25.5,0.6,33.6,3.5,0,0,1,1,0,0,NULL,NULL),(1489,'Oat Milk',NULL,6.52,'100000000218',100,'Dairy','Milk',NULL,'Alpro','Oat Milk','See package','Milk',NULL,10,4,'Dairy',0.7,322,99,9.3,9.1,9.9,45.8,4.1,15,0,1,1,0,0,NULL,NULL),(1490,'Soy Milk',NULL,7.45,'100000000219',100,'Dairy','Milk',NULL,'Lurpak','Soy Milk','See package','Milk',NULL,1,4,'Dairy',5.5,228,108,2.8,10.5,5.7,22.8,9.4,51,0,1,1,0,0,NULL,NULL),(1491,'Greek Yogurt',NULL,10.31,'100000000220',100,'Dairy','Yogurt',NULL,'FreshFarm','Greek Yogurt','See package','Milk',NULL,7,3,'Dairy',1.6,18,418,2.8,22.9,7.5,53.3,6,3,0,1,1,0,0,NULL,NULL),(1492,'Strawberry Yogurt',NULL,14.05,'100000000221',100,'Dairy','Yogurt',NULL,'President','Strawberry Yogurt','See package','Milk',NULL,3,3,'Dairy',2.3,272,475,16.4,2.4,8.8,34.5,5.5,49,0,1,1,0,0,NULL,NULL),(1493,'Vanilla Yogurt',NULL,6.68,'100000000222',100,'Dairy','Yogurt',NULL,'Lurpak','Vanilla Yogurt','See package','Milk',NULL,6,5,'Dairy',18.1,631,454,28.5,5.2,6.6,50,6.6,46,0,1,1,0,0,NULL,NULL),(1494,'Labneh',NULL,23.25,'100000000223',100,'Dairy','Yogurt',NULL,'Alpro','Labneh','See package','Milk',NULL,9,8,'Dairy',1.9,44,48,0.1,19.2,7.2,15.4,2.8,8,0,1,1,0,0,NULL,NULL),(1495,'Cheddar Cheese',NULL,20.7,'100000000224',100,'Dairy','Cheese',NULL,'FreshFarm','Cheddar Cheese','See package','Milk',NULL,1,2,'Dairy',11.7,655,67,19.6,4,4.6,16.4,3.8,88,0,1,1,0,0,NULL,NULL),(1496,'Mozzarella',NULL,23.84,'100000000225',100,'Dairy','Cheese',NULL,'Alpro','Mozzarella','See package','Milk',NULL,3,5,'Dairy',0.2,390,100,10.7,13.3,4.4,36,9,119,0,1,1,0,0,NULL,NULL),(1497,'Cream Cheese',NULL,4.11,'100000000226',100,'Dairy','Cheese',NULL,'Alpro','Cream Cheese','See package','Milk',NULL,4,4,'Dairy',13.9,6,423,7.9,24.4,4.3,56.7,5.1,75,0,1,1,0,0,NULL,NULL),(1498,'Feta',NULL,2.07,'100000000227',100,'Dairy','Cheese',NULL,'President','Feta','See package','Milk',NULL,7,10,'Dairy',17.4,201,75,1.9,9.9,0.1,43.9,4.6,67,0,1,1,0,0,NULL,NULL),(1499,'Parmesan',NULL,14.76,'100000000228',100,'Dairy','Cheese',NULL,'Arla','Parmesan','See package','Milk',NULL,6,5,'Dairy',4.3,190,52,18.9,16.9,5.7,59.5,1.6,78,0,1,1,0,0,NULL,NULL),(1500,'Salted Butter',NULL,7.08,'100000000229',100,'Dairy','Butter',NULL,'FreshFarm','Salted Butter','See package','Milk',NULL,7,1,'Dairy',17,259,448,13.4,27.8,3.4,24.5,9,78,0,1,1,0,0,NULL,NULL),(1501,'Unsalted Butter',NULL,4.12,'100000000230',100,'Dairy','Butter',NULL,'President','Unsalted Butter','See package','Milk',NULL,4,1,'Dairy',16.3,359,337,5.2,17.8,5,14.6,8.2,92,0,1,1,0,0,NULL,NULL),(1502,'White Bread',NULL,20.98,'100000000231',100,'Bakery','Bread',NULL,'Golden Bakery','White Bread','See package',NULL,NULL,8,8,'Bakery',10.8,481,120,26.4,12.8,8.4,26.7,5,49,0,1,0,1,0,NULL,NULL),(1503,'Whole Wheat Bread',NULL,3.63,'100000000232',100,'Bakery','Bread',NULL,'Wonder','Whole Wheat Bread','See package',NULL,NULL,4,1,'Bakery',5.5,488,370,16.1,27.1,8.7,44.9,5.9,90,0,1,0,1,0,NULL,NULL),(1504,'Brown Bread',NULL,19.23,'100000000233',100,'Bakery','Bread',NULL,'Golden Bakery','Brown Bread','See package',NULL,NULL,9,8,'Bakery',15.9,479,275,15.4,22,1.4,47.4,9.7,11,0,1,0,1,0,NULL,NULL),(1505,'Toast Bread',NULL,6.19,'100000000234',100,'Bakery','Bread',NULL,'Wonder','Toast Bread','See package',NULL,NULL,2,2,'Bakery',11.3,670,394,20.7,26.1,2.6,1.7,0.2,61,0,1,0,1,0,NULL,NULL),(1506,'Pita Bread',NULL,24.62,'100000000235',100,'Bakery','Bread',NULL,'Wonder','Pita Bread','See package',NULL,NULL,6,3,'Bakery',11.9,300,148,5.4,5.9,5.6,18.3,2.7,27,0,1,0,1,0,NULL,NULL),(1507,'Sourdough',NULL,8.87,'100000000236',100,'Bakery','Bread',NULL,'Wonder','Sourdough','See package',NULL,NULL,1,2,'Bakery',5.8,204,267,23.8,7.8,7.1,59.6,8.3,10,0,1,0,1,0,NULL,NULL),(1508,'Burger Buns',NULL,24.32,'100000000237',100,'Bakery','Bread',NULL,'Golden Bakery','Burger Buns','See package',NULL,NULL,5,10,'Bakery',0.1,78,43,21.6,28.2,2.4,13.3,2.2,15,0,1,0,1,0,NULL,NULL),(1509,'Hot Dog Buns',NULL,9.09,'100000000238',100,'Bakery','Bread',NULL,'Wonder','Hot Dog Buns','See package',NULL,NULL,10,1,'Bakery',19.6,21,169,5.8,23.3,1.6,22.1,8.2,41,0,1,0,1,0,NULL,NULL),(1510,'Croissant',NULL,15.83,'100000000239',100,'Bakery','Pastry',NULL,'Wonder','Croissant','See package',NULL,NULL,1,3,'Bakery',17.2,80,297,1.9,14.2,8.2,7.6,2.2,32,0,1,0,1,0,NULL,NULL),(1511,'Donut',NULL,24.34,'100000000240',100,'Bakery','Pastry',NULL,'Golden Bakery','Donut','See package',NULL,NULL,5,8,'Bakery',9.1,101,359,29.2,28.4,6.3,17.3,2.3,97,0,1,0,1,0,NULL,NULL),(1512,'Muffin',NULL,19.4,'100000000241',100,'Bakery','Pastry',NULL,'Wonder','Muffin','See package',NULL,NULL,5,5,'Bakery',17.2,674,286,16.7,16.5,7.4,44.7,9,45,0,1,0,1,0,NULL,NULL),(1513,'Bagel',NULL,21.51,'100000000242',100,'Bakery','Pastry',NULL,'Golden Bakery','Bagel','See package',NULL,NULL,1,2,'Bakery',8.7,317,244,6.9,13.2,7.6,35.4,4.5,34,0,1,0,1,0,NULL,NULL),(1514,'Apple',NULL,15.95,'100000000243',100,'Produce','Fruit',NULL,'FreshFarm','Apple','See package',NULL,NULL,4,9,'Produce',11.8,543,200,6.1,9.4,0.7,43.7,6,100,1,1,1,1,0,NULL,NULL),(1515,'Banana',NULL,2.35,'100000000244',100,'Produce','Fruit',NULL,'FreshFarm','Banana','See package',NULL,NULL,8,7,'Produce',2.7,420,455,21.5,25.4,2.5,20,6,4,1,1,1,1,0,NULL,NULL),(1516,'Orange',NULL,19.62,'100000000245',100,'Produce','Fruit',NULL,'FreshFarm','Orange','See package',NULL,NULL,9,10,'Produce',2.3,38,300,19.9,19.6,5.4,5.8,4.4,98,1,1,1,1,0,NULL,NULL),(1517,'Pear',NULL,10.12,'100000000246',100,'Produce','Fruit',NULL,'FreshFarm','Pear','See package',NULL,NULL,1,4,'Produce',7.7,634,398,27.5,2.1,5.5,5,4.5,120,1,1,1,1,0,NULL,NULL),(1518,'Grapes',NULL,8.15,'100000000247',100,'Produce','Fruit',NULL,'FreshFarm','Grapes','See package',NULL,NULL,5,9,'Produce',0.9,89,267,15.9,3.3,1.6,50.6,4.7,48,1,1,1,1,0,NULL,NULL),(1519,'Mango',NULL,22.91,'100000000248',100,'Produce','Fruit',NULL,'FreshFarm','Mango','See package',NULL,NULL,5,9,'Produce',14.7,202,358,18.8,8.4,0.9,55.9,1.2,93,1,1,1,1,0,NULL,NULL),(1520,'Kiwi',NULL,13.73,'100000000249',100,'Produce','Fruit',NULL,'FreshFarm','Kiwi','See package',NULL,NULL,1,6,'Produce',7.8,280,82,16.8,1.6,7.2,14.6,4.2,78,1,1,1,1,0,NULL,NULL),(1521,'Pineapple',NULL,13.94,'100000000250',100,'Produce','Fruit',NULL,'FreshFarm','Pineapple','See package',NULL,NULL,7,4,'Produce',19.6,165,233,6.2,5.4,7,36.5,4.8,64,1,1,1,1,0,NULL,NULL);
/*!40000 ALTER TABLE `products` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recommendation_logs`
--

DROP TABLE IF EXISTS `recommendation_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recommendation_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int NOT NULL,
  `original_product_id` int NOT NULL,
  `recommendation_type` enum('block','warning','suitable') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `suggested_product_id` int DEFAULT NULL,
  `reason_code` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_action` enum('accepted_alt','ignored','added_anyway') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `session_id` (`session_id`),
  KEY `original_product_id` (`original_product_id`),
  KEY `suggested_product_id` (`suggested_product_id`),
  KEY `ix_recommendation_logs_id` (`id`),
  CONSTRAINT `recommendation_logs_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `shopping_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `recommendation_logs_ibfk_2` FOREIGN KEY (`original_product_id`) REFERENCES `products` (`id`),
  CONSTRAINT `recommendation_logs_ibfk_3` FOREIGN KEY (`suggested_product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recommendation_logs`
--

LOCK TABLES `recommendation_logs` WRITE;
/*!40000 ALTER TABLE `recommendation_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `recommendation_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sections`
--

DROP TABLE IF EXISTS `sections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sections` (
  `section_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `marker_id` int DEFAULT NULL,
  `map_x` float DEFAULT NULL,
  `map_y` float DEFAULT NULL,
  PRIMARY KEY (`section_id`),
  UNIQUE KEY `uq_section_marker` (`marker_id`),
  UNIQUE KEY `marker_id` (`marker_id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sections`
--

LOCK TABLES `sections` WRITE;
/*!40000 ALTER TABLE `sections` DISABLE KEYS */;
INSERT INTO `sections` VALUES (1,'Dairy',1,150,200),(2,'Bakery',2,300,200),(3,'Snacks',3,450,200),(4,'Beverages',4,150,400),(5,'Produce',5,300,400),(6,'Meat',6,450,400),(13,'Pantry',7,6,6.5),(14,'Frozen',8,8,6.5),(15,'Entrance',9,1,0.5),(16,'Exit',10,11,0.5),(17,'Payment',11,6,0.5);
/*!40000 ALTER TABLE `sections` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `shelves`
--

DROP TABLE IF EXISTS `shelves`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shelves` (
  `shelf_id` int NOT NULL AUTO_INCREMENT,
  `section_id` int NOT NULL,
  `shelf_label` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`shelf_id`),
  KEY `section_id` (`section_id`),
  CONSTRAINT `shelves_ibfk_1` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `shelves`
--

LOCK TABLES `shelves` WRITE;
/*!40000 ALTER TABLE `shelves` DISABLE KEYS */;
INSERT INTO `shelves` VALUES (1,1,'A1','Dairy Shelf A'),(2,1,'A2','Dairy Shelf B'),(3,2,'B1','Bakery Shelf A'),(4,2,'B2','Bakery Shelf B'),(5,3,'C1','Snacks Shelf A'),(6,3,'C2','Snacks Shelf B'),(7,4,'D1','Beverages Shelf A'),(8,4,'D2','Beverages Shelf B'),(9,5,'E1','Produce Area'),(10,6,'F1','Meat & Deli Counter');
/*!40000 ALTER TABLE `shelves` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `shopping_sessions`
--

DROP TABLE IF EXISTS `shopping_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shopping_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `cart_id` int DEFAULT NULL,
  `cart_rfid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('ACTIVE','PENDING_PAYMENT','PAYMENT_IN_PROGRESS','PAID','CANCELLED','FAILED') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_amount` float DEFAULT NULL,
  `discount` float DEFAULT NULL,
  `started_at` datetime DEFAULT (now()),
  `ended_at` datetime DEFAULT NULL,
  `payment_started_at` datetime DEFAULT NULL,
  `payment_completed_at` datetime DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `cart_id` (`cart_id`),
  KEY `ix_shopping_sessions_cart_rfid` (`cart_rfid`),
  KEY `ix_shopping_sessions_id` (`id`),
  CONSTRAINT `shopping_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `shopping_sessions_ibfk_2` FOREIGN KEY (`cart_id`) REFERENCES `carts` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=83 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `shopping_sessions`
--

LOCK TABLES `shopping_sessions` WRITE;
/*!40000 ALTER TABLE `shopping_sessions` DISABLE KEYS */;
INSERT INTO `shopping_sessions` VALUES (1,3,NULL,NULL,'CANCELLED',0,0,'2026-07-05 00:22:24','2026-07-04 21:22:24',NULL,NULL,NULL),(2,3,NULL,NULL,'PENDING_PAYMENT',3.4,0,'2026-07-05 00:22:24','2026-07-04 21:23:58',NULL,NULL,NULL),(3,3,NULL,NULL,'CANCELLED',0,0,'2026-07-05 00:24:18','2026-07-04 21:24:18',NULL,NULL,NULL),(4,3,NULL,NULL,'CANCELLED',0,0,'2026-07-05 00:24:18','2026-07-06 15:34:45',NULL,NULL,NULL),(5,4,NULL,NULL,'CANCELLED',0,0,'2026-07-06 09:53:00','2026-07-06 06:53:00',NULL,NULL,NULL),(6,4,NULL,NULL,'PENDING_PAYMENT',3.5,0,'2026-07-06 09:53:00','2026-07-06 06:55:26',NULL,NULL,NULL),(7,3,NULL,NULL,'ACTIVE',0,0,'2026-07-06 18:34:45',NULL,NULL,NULL,NULL),(8,5,NULL,NULL,'CANCELLED',0,0,'2026-07-06 20:30:29','2026-07-06 17:30:29',NULL,NULL,NULL),(9,5,NULL,NULL,'PENDING_PAYMENT',15.5,0,'2026-07-06 20:30:29','2026-07-06 17:32:10',NULL,NULL,NULL),(10,5,NULL,NULL,'CANCELLED',0,0,'2026-07-06 20:32:21','2026-07-06 17:32:21',NULL,NULL,NULL),(11,5,NULL,NULL,'ACTIVE',6.5,0,'2026-07-06 20:32:21',NULL,NULL,NULL,NULL),(12,1,NULL,NULL,'CANCELLED',0,0,'2026-07-06 21:11:52','2026-07-06 18:11:52',NULL,NULL,NULL),(13,1,NULL,NULL,'ACTIVE',0,0,'2026-07-06 21:11:52',NULL,NULL,NULL,NULL),(14,4,NULL,NULL,'ACTIVE',6,0,'2026-07-06 21:12:10',NULL,NULL,NULL,NULL),(15,6,NULL,NULL,'CANCELLED',0,0,'2026-07-07 10:46:09','2026-07-07 07:46:09',NULL,NULL,NULL),(16,6,NULL,NULL,'PENDING_PAYMENT',9.1,0,'2026-07-07 10:46:09','2026-07-07 07:50:10',NULL,NULL,NULL),(17,6,NULL,NULL,'CANCELLED',0,0,'2026-07-07 10:54:37','2026-07-07 07:54:37',NULL,NULL,NULL),(18,6,NULL,NULL,'ACTIVE',2,0,'2026-07-07 10:54:37',NULL,NULL,NULL,NULL),(19,7,NULL,NULL,'PENDING_PAYMENT',1.5,0,'2026-07-10 16:24:07','2026-07-10 13:24:08',NULL,NULL,NULL),(20,8,NULL,NULL,'CANCELLED',0,0,'2026-07-11 13:12:38','2026-07-11 10:12:39',NULL,NULL,NULL),(21,8,NULL,NULL,'CANCELLED',0,0,'2026-07-11 13:12:38','2026-07-11 10:16:02',NULL,NULL,NULL),(22,8,NULL,NULL,'PENDING_PAYMENT',6.5,0,'2026-07-11 13:16:02','2026-07-11 10:17:19',NULL,NULL,NULL),(23,8,NULL,NULL,'ACTIVE',0,0,'2026-07-11 13:17:31',NULL,NULL,NULL,NULL),(24,9,NULL,NULL,'CANCELLED',0,0,'2026-07-14 20:56:59','2026-07-14 17:57:00',NULL,NULL,NULL),(25,9,NULL,NULL,'CANCELLED',0,0,'2026-07-14 20:57:00','2026-07-28 18:04:17',NULL,NULL,NULL),(26,10,NULL,NULL,'CANCELLED',0,0,'2026-07-21 19:35:08','2026-07-21 16:35:08',NULL,NULL,NULL),(27,10,NULL,NULL,'ACTIVE',0,0,'2026-07-21 19:35:08',NULL,NULL,NULL,NULL),(28,11,NULL,NULL,'CANCELLED',0,0,'2026-07-22 20:44:56','2026-07-22 17:44:57',NULL,NULL,NULL),(29,11,NULL,NULL,'ACTIVE',0,0,'2026-07-22 20:44:56',NULL,NULL,NULL,NULL),(30,12,NULL,NULL,'CANCELLED',0,0,'2026-07-24 00:35:46','2026-07-23 21:35:47',NULL,NULL,NULL),(31,12,NULL,NULL,'CANCELLED',2.9,0,'2026-07-24 00:35:46','2026-07-26 11:30:35',NULL,NULL,NULL),(32,12,NULL,NULL,'CANCELLED',124.69,0,'2026-07-26 14:30:34','2026-07-26 17:41:18',NULL,NULL,NULL),(33,12,NULL,NULL,'CANCELLED',0,0,'2026-07-26 20:41:18','2026-07-26 18:27:46',NULL,NULL,NULL),(34,12,NULL,NULL,'CANCELLED',0,0,'2026-07-26 20:41:18','2026-08-02 17:33:09',NULL,NULL,NULL),(35,12,NULL,NULL,'CANCELLED',0,0,'2026-07-26 21:27:45','2026-08-02 18:37:29',NULL,NULL,NULL),(36,12,NULL,NULL,'CANCELLED',0,0,'2026-07-26 21:27:45','2026-08-02 18:37:56',NULL,NULL,NULL),(37,9,NULL,NULL,'CANCELLED',13.59,0,'2026-07-28 21:04:16','2026-07-28 18:05:22',NULL,NULL,NULL),(38,9,NULL,NULL,'CANCELLED',95.28,0,'2026-07-28 21:05:21','2026-08-01 16:52:41',NULL,NULL,NULL),(39,13,NULL,NULL,'CANCELLED',0,0,'2026-07-29 21:06:17','2026-07-29 18:06:17',NULL,NULL,NULL),(40,13,NULL,NULL,'CANCELLED',8.95,0,'2026-07-29 21:06:17','2026-07-29 18:07:59',NULL,NULL,NULL),(41,13,NULL,NULL,'CANCELLED',46.5,0,'2026-07-29 21:07:58','2026-07-29 20:07:51',NULL,NULL,NULL),(42,13,NULL,NULL,'PENDING_PAYMENT',22.18,0,'2026-07-29 23:07:51','2026-07-30 07:39:28',NULL,NULL,NULL),(43,13,NULL,NULL,'CANCELLED',0,0,'2026-07-30 10:44:40','2026-07-30 07:44:41',NULL,NULL,NULL),(44,13,NULL,NULL,'CANCELLED',24.02,0,'2026-07-30 10:44:40','2026-07-30 07:53:45',NULL,NULL,NULL),(45,13,NULL,NULL,'ACTIVE',0,0,'2026-07-30 10:53:44',NULL,NULL,NULL,NULL),(46,13,NULL,NULL,'ACTIVE',13.73,0,'2026-07-30 10:53:44',NULL,NULL,NULL,NULL),(47,9,NULL,NULL,'CANCELLED',0,0,'2026-08-01 19:52:41','2026-08-03 17:37:17',NULL,NULL,NULL),(48,12,NULL,NULL,'CANCELLED',19.95,0,'2026-08-02 20:33:09','2026-08-02 18:49:47',NULL,NULL,NULL),(49,12,NULL,NULL,'CANCELLED',19.95,0,'2026-08-02 21:37:29','2026-08-02 19:03:02',NULL,NULL,NULL),(50,12,NULL,NULL,'CANCELLED',24.02,0,'2026-08-02 21:37:55','2026-08-02 19:06:25',NULL,NULL,NULL),(51,12,NULL,NULL,'CANCELLED',21.09,0,'2026-08-02 21:49:46','2026-08-02 20:35:41',NULL,NULL,NULL),(52,12,NULL,NULL,'ACTIVE',0,0,'2026-08-02 22:03:01',NULL,NULL,NULL,NULL),(53,12,NULL,NULL,'ACTIVE',21.09,0,'2026-08-02 22:06:25',NULL,NULL,NULL,NULL),(54,12,NULL,NULL,'ACTIVE',0,0,'2026-08-02 23:35:41',NULL,NULL,NULL,NULL),(55,9,NULL,NULL,'CANCELLED',13.17,0,'2026-08-03 20:37:17','2026-08-03 17:37:25',NULL,NULL,NULL),(56,9,NULL,NULL,'CANCELLED',26.34,0,'2026-08-03 20:37:24','2026-08-03 17:38:39',NULL,NULL,NULL),(57,9,NULL,NULL,'CANCELLED',24.02,0,'2026-08-03 20:38:38','2026-08-03 19:02:41',NULL,NULL,NULL),(58,9,NULL,NULL,'CANCELLED',24.02,0,'2026-08-03 22:02:40','2026-08-03 19:03:00',NULL,NULL,NULL),(59,9,NULL,NULL,'PENDING_PAYMENT',28.78,0,'2026-08-03 22:02:59','2026-08-03 19:08:10',NULL,NULL,NULL),(60,9,NULL,NULL,'CANCELLED',0,0,'2026-08-03 22:35:13','2026-08-04 17:47:45',NULL,NULL,NULL),(61,9,NULL,NULL,'CANCELLED',167.03,0,'2026-08-03 22:35:13','2026-08-09 07:54:34',NULL,NULL,NULL),(62,9,NULL,NULL,'CANCELLED',45.78,0,'2026-08-04 20:47:44','2026-08-10 21:55:00',NULL,NULL,NULL),(63,9,NULL,NULL,'CANCELLED',0,0,'2026-08-09 10:54:33','2026-08-13 12:29:41',NULL,NULL,NULL),(64,9,NULL,NULL,'CANCELLED',23.15,0,'2026-08-11 00:54:59','2026-08-13 12:34:36',NULL,NULL,NULL),(65,9,NULL,NULL,'CANCELLED',0,0,'2026-08-13 15:29:40','2026-08-13 12:36:30',NULL,NULL,NULL),(66,9,NULL,NULL,'CANCELLED',18.63,0,'2026-08-13 15:34:36','2026-08-13 12:39:36',NULL,NULL,NULL),(67,9,NULL,NULL,'PENDING_PAYMENT',23.19,0,'2026-08-13 15:36:29','2026-08-13 12:39:15',NULL,NULL,NULL),(68,9,NULL,NULL,'CANCELLED',3.4,0,'2026-08-13 15:39:36','2026-08-13 12:40:19',NULL,NULL,NULL),(69,9,NULL,NULL,'PENDING_PAYMENT',23.19,0,'2026-08-13 15:40:19','2026-08-13 12:43:04',NULL,NULL,NULL),(70,9,NULL,NULL,'CANCELLED',0,0,'2026-08-15 21:32:53','2026-08-16 18:48:59',NULL,NULL,NULL),(71,9,NULL,NULL,'CANCELLED',0,0,'2026-08-16 21:48:58','2026-08-16 21:14:56',NULL,NULL,NULL),(72,9,NULL,NULL,'CANCELLED',0,0,'2026-08-17 00:14:56','2026-08-17 19:28:09',NULL,NULL,NULL),(73,9,NULL,NULL,'CANCELLED',0,0,'2026-08-17 22:28:09','2026-08-19 08:16:27',NULL,NULL,NULL),(74,9,NULL,NULL,'CANCELLED',0,0,'2026-08-19 11:16:26','2026-08-19 08:18:51',NULL,NULL,NULL),(75,9,NULL,NULL,'CANCELLED',0,0,'2026-08-19 11:18:50','2026-08-19 08:25:19',NULL,NULL,NULL),(76,9,NULL,NULL,'ACTIVE',40.36,0,'2026-08-19 11:25:19',NULL,NULL,NULL,NULL),(77,7,NULL,NULL,'ACTIVE',0,0,'2026-08-21 16:21:27',NULL,NULL,NULL,NULL),(78,7,NULL,NULL,'ACTIVE',0,0,'2026-08-21 16:21:27',NULL,NULL,NULL,NULL),(79,14,NULL,NULL,'CANCELLED',0,0,'2026-08-21 16:22:43','2026-08-21 13:22:44',NULL,NULL,NULL),(80,14,NULL,NULL,'CANCELLED',0,0,'2026-08-21 16:22:43','2026-08-21 14:44:45',NULL,NULL,NULL),(81,14,NULL,NULL,'CANCELLED',0,0,'2026-08-21 17:44:44','2026-08-21 16:09:21',NULL,NULL,NULL),(82,14,1,'RFIDDEFAULT001','ACTIVE',28.37,0,'2026-08-21 19:09:21',NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `shopping_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `theft_logs`
--

DROP TABLE IF EXISTS `theft_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `theft_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int DEFAULT NULL,
  `alert_type` enum('UNSCANNED_ITEM','SUSPICIOUS_MOVEMENT','ITEM_CONCEALED','MULTIPLE_ITEMS','BRAKE_ACTIVATED','UNSCANNED_IN_CART','PROLONGED_HOLDING') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `confidence_score` float DEFAULT NULL,
  `brake_activated` tinyint(1) DEFAULT NULL,
  `customer_notified` tinyint(1) DEFAULT NULL,
  `security_notified` tinyint(1) DEFAULT NULL,
  `resolved` tinyint(1) DEFAULT NULL,
  `resolved_by_user_id` int DEFAULT NULL,
  `detected_at` datetime DEFAULT (now()),
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `session_id` (`session_id`),
  KEY `ix_theft_logs_id` (`id`),
  CONSTRAINT `theft_logs_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `shopping_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `theft_logs`
--

LOCK TABLES `theft_logs` WRITE;
/*!40000 ALTER TABLE `theft_logs` DISABLE KEYS */;
INSERT INTO `theft_logs` VALUES (1,NULL,'UNSCANNED_IN_CART','Product (cup) detected in cart zone without any scan registered',0.75,0,1,0,0,NULL,'2026-07-10 16:26:29',NULL);
/*!40000 ALTER TABLE `theft_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('CUSTOMER','OWNER','SECURITY') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `age` int DEFAULT NULL,
  `gender` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `allergies` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `other_health_notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `recommendations_enabled` tinyint(1) NOT NULL,
  `onboarding_completed` tinyint(1) NOT NULL,
  `business_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `license_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `badge_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `shift_schedule` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `clearance_level` int DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Admin Owner','admin@neoshop.com','$2b$12$i4sJ2.ElgTAQZ7cz/K/g2.Yj1FW8HH1qG.XClEQ0c4eSpYOQ02iXe','OWNER',1,NULL,NULL,'[]',NULL,1,0,NULL,NULL,NULL,NULL,1,'2026-07-05 00:18:20',NULL),(2,'Security Officer','security@neoshop.com','$2b$12$8DB8N5Xdbf5bTrewnGtv/OFHFHRw1V2s1GdoG3.wmrDRdpnvguRu2','SECURITY',1,NULL,NULL,'[]',NULL,1,0,NULL,NULL,NULL,NULL,1,'2026-07-05 00:18:20',NULL),(3,'arwa','arwa1@gmail.com','$2b$12$nQR8k5da2EMlylOfJUaEAeWx0La.EV.hs3lFYOISXrpeJ/GK3fAbm','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"milk\", \"peanuts\"]',NULL,0,1,NULL,NULL,NULL,NULL,1,'2026-07-05 00:22:11','2026-07-05 00:24:17'),(4,'arwa','arwa22@gmail.com','$2b$12$Rsyn1onQEP2M/JP9va9n3.irE6tlnkTpb/Ws4JtGAS8PD9nrVXcoy','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"milk\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-06 09:51:33','2026-07-06 09:53:00'),(5,'arwa','arwa222@gmail.com','$2b$12$C1KdZ31iScorXwuyNqCPaufH1.2DRs3eRgF9gYkXC34o3pqhpW6Pi','CUSTOMER',1,NULL,NULL,'[\"sesame\", \"soy\", \"nuts\", \"peanuts\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-06 20:30:22','2026-07-06 20:32:42'),(6,'arwa','aa@gmail.com','$2b$12$lec.c.3Omu3B2/X6TlOPuux.CAaClH3SGd4nfyjJWJ8L5ofZuXfWC','CUSTOMER',1,NULL,NULL,'[\"nuts\", \"soy\", \"peanuts\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-07 10:45:58','2026-07-07 10:49:57'),(7,'CV Test','cvtest@neoshop.com','$2b$12$rPPCGAAdmQvP9gIosFkEX.Ztg6kt65uictgOONNLKa94yn6ZW8RIi','CUSTOMER',1,NULL,NULL,'[]',NULL,1,0,NULL,NULL,NULL,NULL,1,'2026-07-10 16:24:07',NULL),(8,'arwa','arwaa@gmail.com','$2b$12$.nWhs79pLAQHJ/KarvoDHeICMNwmmQWhiOWdeuthrwqEgp.T6Tkhi','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"sesame\", \"peanuts\", \"soy\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-11 13:12:31','2026-07-11 13:12:38'),(9,'arwaa','arwaaa@gmail.com','$2b$12$i.swuSTGtuu9K3JClizPa.JEEOqdBXW4nHCvr71guoLHaL7nRrUbG','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"milk\", \"nuts\", \"peanuts\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-14 20:56:51','2026-07-14 20:56:59'),(10,'aaaa','aaaaaaaa@gmail.com','$2b$12$rXK9lstetNaMemo.TZ5ZLeCBYsDQROtlhAUkOYBcbNHFnol0yq8ua','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"milk\", \"soy\", \"nuts\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-21 19:34:43','2026-07-21 19:35:08'),(11,'arwahaj','arwa@gmail.com','$2b$12$JxC3bUQAW8nCcvKrDtl4Xuvbw.fn5oqXwlusQpiilQQO/hoVxVKaG','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"soy\", \"nuts\", \"peanuts\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-22 20:44:47','2026-07-22 20:44:56'),(12,'arwaaa','arwaaaa@gmail.com','$2b$12$8rPz/tm/5ega74655nBNw.Bjlo7ze66zkgcIdsMstLkIVYTP4R0Hu','CUSTOMER',1,NULL,NULL,'[\"eggs\", \"nuts\", \"peanuts\", \"soy\"]',NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-24 00:35:38','2026-07-24 00:35:46'),(13,'ARWA','arwaarwaarwa@gmail.com','$2b$12$YU1jySNK9ZQYtx6uN2dUyeGVmJGgIBJpoCSbbWnlKh.zg0gspGox6','CUSTOMER',1,NULL,NULL,NULL,NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-07-29 21:06:03','2026-07-29 21:06:16'),(14,'belal edoor','belaledoor25@gmail.com','$2b$12$i2XJNklEfEliC7fwRmI9O.zSfGZz7CyC4eyU1zZlOP0S6sS3RmotS','CUSTOMER',1,NULL,NULL,NULL,NULL,1,1,NULL,NULL,NULL,NULL,1,'2026-08-21 16:22:32','2026-08-21 16:22:43');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-22  0:05:57
