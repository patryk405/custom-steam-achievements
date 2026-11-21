import {sqliteTable,text,integer} from 'drizzle-orm/sqlite-core';
export const packs=sqliteTable('packs',{
 id:text('id').primaryKey(),owner:text('owner').notNull(),title:text('title').notNull(),author:text('author').notNull(),description:text('description').notNull(),game:text('game').notNull(),version:text('version').notNull(),payload:text('payload').notNull(),count:integer('count').notNull(),downloads:integer('downloads').notNull().default(0),createdAt:integer('created_at').notNull()
});
export const steamSessions=sqliteTable('steam_sessions',{tokenHash:text('token_hash').primaryKey(),steamId:text('steam_id').notNull(),kind:text('kind').notNull(),name:text('name').notNull(),createdAt:integer('created_at').notNull(),expiresAt:integer('expires_at').notNull()});
export const steamFlows=sqliteTable('steam_flows',{stateHash:text('state_hash').primaryKey(),device:text('device'),expiresAt:integer('expires_at').notNull()});
export const steamNonces=sqliteTable('steam_nonces',{nonce:text('nonce').primaryKey(),expiresAt:integer('expires_at').notNull()});
export const steamDevices=sqliteTable('steam_devices',{id:text('id').primaryKey(),tokenHash:text('token_hash').notNull(),expectedSteamId:text('expected_steam_id').notNull(),name:text('name').notNull(),steamId:text('steam_id'),expiresAt:integer('expires_at').notNull()});
export const cloudProgress=sqliteTable('cloud_progress',{key:text('key').primaryKey(),steamId:text('steam_id').notNull(),game:text('game').notNull(),achievement:text('achievement').notNull(),current:integer('current').notNull(),unlockedAt:integer('unlocked_at'),updatedAt:integer('updated_at').notNull()});
export const cloudRates=sqliteTable('cloud_rates',{key:text('key').primaryKey(),count:integer('count').notNull(),expiresAt:integer('expires_at').notNull()});
