import 'reflect-metadata'; // Required by TypeORM
import { DataSource, DataSourceOptions } from 'typeorm';
import dotenv from 'dotenv';

dotenv.config(); // Ensure environment variables are loaded

// Basic check for required environment variables
if (!process.env.PG_HOST || !process.env.PG_PORT || !process.env.PG_USER || !process.env.PG_PASSWORD || !process.env.PG_DATABASE) {
    console.error("Error: Missing PostgreSQL environment variables. Please check your .env file.");
    process.exit(1);
}

export const AppDataSourceOptions: DataSourceOptions = {
    type: 'postgres',
    host: process.env.PG_HOST,
    port: parseInt(process.env.PG_PORT, 10),
    username: process.env.PG_USER,
    password: process.env.PG_PASSWORD,
    database: process.env.PG_DATABASE,
    synchronize: process.env.NODE_ENV === 'development', // Sync schema in dev mode only - BE CAREFUL IN PRODUCTION
    logging: process.env.NODE_ENV === 'development' ? ['query', 'error'] : ['error'], // Log queries in dev
    entities: [__dirname + '/../entities/**/*.entity{.ts,.js}'], // Path to your entities
    migrations: [__dirname + '/../migrations/**/*{.ts,.js}'], // Path to your migrations
    subscribers: [__dirname + '/../subscribers/**/*{.ts,.js}'], // Path to your subscribers
};

export const AppDataSource = new DataSource(AppDataSourceOptions); 