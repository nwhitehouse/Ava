import 'reflect-metadata'; // Must be the first import
import express, { Request, Response } from 'express';
import dotenv from 'dotenv';
import cors from 'cors'; // Import cors
import { AppDataSource } from './config/data-source'; // Import TypeORM data source
import weaviateClient from './config/weaviate-client'; // Import Weaviate client
import userRoutes from './routes/user.routes'; // Import user routes
import mockRoutes from './routes/mock.routes'; // Import mock routes

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
    // IMPORTANT: Allow requests from Vite dev server (adjust port if needed)
    // In production, restrict this to your actual frontend domain
    const corsOptions = {
      origin: ['http://localhost:5173', 'http://127.0.0.1:5173'], // Add other origins if needed
      optionsSuccessStatus: 200 // some legacy browsers (IE11, various SmartTVs) choke on 204
    };
    app.use(cors(corsOptions));
    app.use(express.json()); // Parse JSON bodies

    // Routes
    app.get('/', (req: Request, res: Response) => {
      res.send('Ava Backend Root - API is available under /api');
    });
    app.use('/api/users', userRoutes); // Mount user routes
    app.use('/api/mock', mockRoutes); // Mount mock routes
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
