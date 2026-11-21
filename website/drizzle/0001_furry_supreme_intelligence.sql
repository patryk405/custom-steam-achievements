CREATE TABLE `cloud_progress` (
	`key` text PRIMARY KEY NOT NULL,
	`steam_id` text NOT NULL,
	`game` text NOT NULL,
	`achievement` text NOT NULL,
	`current` integer NOT NULL,
	`unlocked_at` integer,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `steam_devices` (
	`id` text PRIMARY KEY NOT NULL,
	`token_hash` text NOT NULL,
	`expected_steam_id` text NOT NULL,
	`name` text NOT NULL,
	`steam_id` text,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `steam_flows` (
	`state_hash` text PRIMARY KEY NOT NULL,
	`device` text,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `steam_nonces` (
	`nonce` text PRIMARY KEY NOT NULL,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `steam_sessions` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`steam_id` text NOT NULL,
	`kind` text NOT NULL,
	`name` text NOT NULL,
	`created_at` integer NOT NULL,
	`expires_at` integer NOT NULL
);
