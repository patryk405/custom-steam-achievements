CREATE TABLE `packs` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`title` text NOT NULL,
	`author` text NOT NULL,
	`description` text NOT NULL,
	`game` text NOT NULL,
	`version` text NOT NULL,
	`payload` text NOT NULL,
	`count` integer NOT NULL,
	`downloads` integer DEFAULT 0 NOT NULL,
	`created_at` integer NOT NULL
);
