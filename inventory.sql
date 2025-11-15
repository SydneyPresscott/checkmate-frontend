
-- Enable foreign key support in SQLite
PRAGMA foreign_keys = ON;

--
-- Table structure for table `products`
--
DROP TABLE IF EXISTS `products`;

CREATE TABLE `products` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT NOT NULL,
  `category` TEXT,
  `reorder_level` INTEGER DEFAULT 10,
  `is_deleted` INTEGER DEFAULT 0
);

--
-- Dumping data for table `products`
--
INSERT INTO `products` (`id`, `name`, `category`, `reorder_level`, `is_deleted`) VALUES
(1, 'Milk Cartons', 'Dairy', 10, 0),
(2, 'Dozen Eggs', 'Dairy', 20, 0),
(3, 'Loaf of Bread', 'Bakery', 15, 0),
(4, 'Apples (Bag)', 'Produce', 10, 0),
(5, 'Cereal Box', 'Pantry', 25, 0),
(6, 'Chicken Breast (kg)', 'Meat', 10, 0),
(7, 'Orange Juice', 'Beverages', 15, 0);

--
-- Table structure for table `batches`
--
DROP TABLE IF EXISTS `batches`;

CREATE TABLE `batches` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `product_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL DEFAULT 0,
  `entry_date` DATE NOT NULL,
  `expiry_date` DATE,
  FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
);

--
-- Dumping data for table `batches`
--
-- Note: Dates are set around November 2025 to match your screenshots.
--
INSERT INTO `batches` (`id`, `product_id`, `quantity`, `entry_date`, `expiry_date`) VALUES
(1, 1, 0, '2025-11-14', '2025-11-24'), 
(2, 1, 0, '2025-11-14', '2025-11-16'), 
(3, 1, 50, '2025-11-14', '2025-12-14'), 
(4, 2, 100, '2025-11-10', '2025-12-01'), 
(5, 3, 75, '2025-11-13', '2025-11-20'), 
(6, 4, 120, '2025-11-12', '2025-11-26'), 
(7, 5, 80, '2025-10-30', '2026-05-01'), 
(8, 6, 30, '2025-11-14', '2025-11-21'), 
(9, 6, 40, '2025-11-15', '2025-11-22'), 
(10, 7, 60, '2025-11-05', '2026-02-05'),
(11, 2, 50, '2025-11-01', '2025-11-10');
