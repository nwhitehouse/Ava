import 'reflect-metadata'; // Must be the first import
import express, { Request, Response } from 'express';
import dotenv from 'dotenv';
import { AppDataSource } from './config/data-source'; // Import TypeORM data source
import weaviateClient from './config/weaviate-client'; // Import Weaviate client
import userRoutes from './routes/user.routes'; // Import user routes

dotenv.config(); // Load environment variables from .env file

// --- App Initialization ---
async function initializeApp() {
  try {
    // Initialize TypeORM connection
    await AppDataSource.initialize();
    console.log("[database]: TypeORM Data Source has been initialized!");

    // Check Weaviate connection
    const meta = await weaviateClient.misc.metaGetter().do();
    console.log(`[database]: Connected to Weaviate host: ${meta.hostname} version: ${meta.version}`);

    // --- Express App Setup ---
    const app = express();
    const port = process.env.PORT || 3001;

    // Middleware
    app.use(express.json()); // Parse JSON bodies
    // Add other middleware here (CORS, logging, etc.) as needed

    // Routes
    app.get('/', (req: Request, res: Response) => {
      res.send('Ava Backend Root - API is available under /api');
    });
    app.use('/api/users', userRoutes); // Mount user routes
    // Add other routes here

    // Start Server
    app.listen(port, () => {
      console.log(`[server]: Server is running at http://localhost:${port}`);
    });

  } catch (error) {
    console.error("[server]: Error during server initialization:", error);
    process.exit(1);
  }
}

initializeApp(); // Start the application
