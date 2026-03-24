-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: travel_crm
-- ------------------------------------------------------
-- Server version	8.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `leads`
--

DROP TABLE IF EXISTS `leads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `leads` (
  `id` int NOT NULL AUTO_INCREMENT,
  `lead_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mobile` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alt_mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tour_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `travel_date` date DEFAULT NULL,
  `pickup_location` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `drop_location` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adults` int DEFAULT '1',
  `children` int DEFAULT '0',
  `hotel_category` enum('Budget','Deluxe','Premium') COLLATE utf8mb4_unicode_ci DEFAULT 'Budget',
  `meal_plan` enum('CP','MAP','AP','EP') COLLATE utf8mb4_unicode_ci DEFAULT 'MAP',
  `vehicle_type` enum('Sedan','SUV','Innova','Tempo Traveller','Mini Bus','Bus') COLLATE utf8mb4_unicode_ci DEFAULT 'Sedan',
  `lead_source` enum('Call','Website','WhatsApp','Referral','Walk-in','Other') COLLATE utf8mb4_unicode_ci DEFAULT 'Call',
  `assigned_to` int DEFAULT NULL,
  `status` enum('New Lead','Follow-up','Negotiation','Booked','Lost') COLLATE utf8mb4_unicode_ci DEFAULT 'New Lead',
  `enquiry_date` date DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lead_id` (`lead_id`),
  KEY `idx_mobile` (`mobile`),
  KEY `idx_status` (`status`),
  KEY `idx_assigned` (`assigned_to`),
  KEY `idx_lead_id` (`lead_id`),
  CONSTRAINT `leads_ibfk_1` FOREIGN KEY (`assigned_to`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `leads`
--

LOCK TABLES `leads` WRITE;
/*!40000 ALTER TABLE `leads` DISABLE KEYS */;
INSERT INTO `leads` VALUES (1,'LEAD-2026-00001','Chirag Singh','7453842945','07453842945','','Greater Noida','Ayodhya','2026-03-09','Noida','Ayodhya Dham',2,1,'Deluxe','MAP','Sedan','Call',2,'Follow-up','2026-03-08','Enquary','2026-03-08 07:28:16','2026-03-08 10:26:20'),(2,'LEAD-2026-00002','Dipanshu','8868066231','7500528418','di@gmail.com','Greater Noida','Meerut','2026-03-10','Muzaffarnagar','Meerut',2,1,'Deluxe','MAP','Innova','Website',2,'New Lead','2026-03-08','Query','2026-03-08 11:07:27','2026-03-08 11:07:27');
/*!40000 ALTER TABLE `leads` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-19  5:06:35
