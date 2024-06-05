package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/gofiber/fiber/v2"
)

var ctx = context.Background()

// Define the structure for the pool details
type Pool struct {
	PoolID          string  `json:"pool_id"`
	BaseRate        float64 `json:"base_rate"`
	BaseSlope       float64 `json:"base_slope"`
	KinkSlope       float64 `json:"kink_slope"`
	OptimalUtilRate float64 `json:"optimal_util_rate"`
	BorrowAmount    float64 `json:"borrow_amount"`
}

type InputRequest struct {
	AssetsAndPools struct {
		TotalAssets float64         `json:"total_assets"`
		Pools       map[string]Pool `json:"pools"`
	} `json:"assets_and_pools"`
}

type FinalResponse struct {
	AssetsAndPools struct {
		TotalAssets float64         `json:"total_assets"`
		Pools       map[string]Pool `json:"pools"`
	} `json:"assets_and_pools"`
	Allocations map[string]float64 `json:"allocations"`
	Name        string             `json:"name"`
}

func main() {
	// Define the port flag
	port := flag.String("port", "3001", "Port to run the Fiber app on")
	redisPort := flag.String("redis.port", "6379", "Port to run the Redis server on")
	redisHost := flag.String("redis.host", "localhost", "Port to run the Redis server on")
	fwdHost := flag.String("fwd.host", "localhost", "Host to forward requests to")
	fwdPort := flag.String("fwd.port", "3000", "Port to forward requests to")

	// Parse the command-line flags
	flag.Parse()

	// Create a new Fiber instance
	app := fiber.New()

	// Initialize Redis client
	rdb := redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%s", *redisHost, *redisPort), // Redis server address
		Password: "",                                           // No password set
		DB:       0,                                            // Use default DB
	})

	// Define a POST route to handle JSON requests
	app.Post("/AllocateAssets", func(c *fiber.Ctx) error {
		ip := c.IP()
		path := c.Path()
		log.Printf("Received request IP: %s, Path: %s\n", ip, path)

		// Forward the request to another server
		forwardURL := fmt.Sprintf("http://%s:%s/AllocateAssets", *fwdHost, *fwdPort)
		reqBody := c.Body()

		// Use the raw request body as the cache key
		// cacheKey := string(reqBody)

		// Hash the request body to create a Redis key
		hash := sha256.Sum256(reqBody)
		cacheKey := hex.EncodeToString(hash[:])

		// Check if response is in cache
		cacheResponse, err := rdb.Get(ctx, cacheKey).Result()
		if err == nil {
			log.Printf("IP: %s, Path: %s. Cache hit\n", ip, path)
			return c.SendString(cacheResponse)
		}

		resp, err := http.Post(forwardURL, "application/json", bytes.NewBuffer(reqBody))
		if err != nil {
			log.Printf("IP: %s, Path: %s. ERROR: Cannot forward request: %s\n", ip, path, err)
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Cannot forward request",
			})
		}
		defer resp.Body.Close()

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("IP: %s, Path: %s. ERROR: Cannot read response body: %s\n", ip, path, err)
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Cannot read response body",
			})
		}

		if resp.StatusCode != http.StatusOK {
			log.Printf("IP: %s, Path: %s. ERROR: Received non-OK response from forwarded server: %s\n", ip, path, body)
			return c.Status(resp.StatusCode).Send(body)
		}

		// Cache the response
		err = rdb.Set(ctx, cacheKey, body, 10*time.Minute).Err()
		if err != nil {
			log.Printf("IP: %s, Path: %s. ERROR: Cannot cache response: %s\n", ip, path, err)
		}

		log.Printf("IP: %s, Path: %s. Forwarded request successfully\n", ip, path)
		return c.Send(body)
	})

	// Start the server on port 3000
	log.Printf("Starting server on port %s...", *port)
	log.Printf("Redis server %s:%s...", *redisHost, *redisPort)
	log.Printf("Forwarding destination %s:%s...", *fwdHost, *fwdPort)
	log.Fatal(app.Listen(fmt.Sprintf(":%s", *port)))
}
