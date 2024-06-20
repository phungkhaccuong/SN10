package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
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
	ReserveSize     float64 `json:"reserve_size"`
}

type InputRequest struct {
	AssetsAndPools struct {
		TotalAssets float64         `json:"total_assets"`
		Pools       map[string]Pool `json:"pools"`
	} `json:"assets_and_pools"`
	redis_key string `json:"redis_key"`
}

type FinalResponse struct {
	AssetsAndPools struct {
		TotalAssets float64         `json:"total_assets"`
		Pools       map[string]Pool `json:"pools"`
	} `json:"assets_and_pools"`
	Allocations map[string]float64 `json:"allocations"`
	Name        string             `json:"name"`
}

func hashObject(obj interface{}) (string, error) {
	// Serialize the object to JSON
	data, err := json.Marshal(obj)
	if err != nil {
		return "", err
	}

	// log.Printf("String to hash: %s\n", string(data))

	// Compute the SHA-256 hash
	hash := sha256.Sum256(data)

	// Convert the hash to a hexadecimal string
	hashStr := hex.EncodeToString(hash[:])
	// log.Printf("Key: %s\n", hashStr)
	return hashStr, nil
}

func waitForResponse(c *fiber.Ctx, key string, keyIndex string, rdb *redis.Client) error {
	for {
		res, err := rdb.Get(ctx, key+"-"+keyIndex).Result()
		if err == redis.Nil {
			time.Sleep(20 * time.Millisecond) // Polling interval, adjust as needed
			continue
		} else if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error communicating with Redis")
		}

		log.Printf("Response from cached after waiting for lock")
		c.Set(fiber.HeaderContentType, fiber.MIMEApplicationJSON)
		// Write the cached response
		return c.SendString(res)
	}
}

func main() {
	// Define the port flag
	port := flag.String("port", "3001", "Port to run the Fiber app on")
	redisPort := flag.String("redis.port", "6379", "Port to run the Redis server on")
	redisHost := flag.String("redis.host", "localhost", "Port to run the Redis server on")
	fwdHost := flag.String("fwd.host", "localhost", "Host to forward requests to")
	fwdPort := flag.String("fwd.port", "3000", "Port to forward requests to")
	keyIndex := flag.String("key.index", "0", "Index of the key to use for caching")

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

		// Print the body
		// log.Printf("Request Body: %s\n", string(reqBody))

		// Use the raw request body as the cache key
		// cacheKey := string(reqBody)

		// TODO: this does not work because of nonce field
		// Hash the request body to create a Redis key
		// hash := sha256.Sum256(reqBody)
		// cacheKey := hex.EncodeToString(hash[:])

		// Parse the JSON request body into the InputRequest struct
		req := new(InputRequest)
		if err := json.Unmarshal(reqBody, req); err != nil {
			log.Printf("IP: %s, Path: %s. ERROR: Cannot parse JSON from body: %s\n", ip, path, c.Body())
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Cannot parse JSON",
			})
		}
		// Hash the request object to create a Redis key
		cacheKey, err := hashObject(req)
		if err != nil {
			log.Printf("IP: %s, Path: %s. ERROR: Cannot hash request object: %s\n", ip, path, err)
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Cannot hash request object",
			})
		}

		req.redis_key = cacheKey

		redisKey := "lock:" + cacheKey
		// Try to acquire the lock in Redis
		lock, err := rdb.SetNX(ctx, redisKey, "locked", 10*time.Second).Result()
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error communicating with Redis")
		}

		if !lock {
			// If lock is not acquired, wait for the existing request to complete
			return waitForResponse(c, cacheKey, *keyIndex, rdb)
		}

		// If lock is acquired, process the request
		defer rdb.Del(ctx, redisKey) // Release the lock when done

		// Check if response is in cache
		cacheResponse, err := rdb.Get(ctx, "response:"+cacheKey).Result()
		if err == nil {
			log.Printf("IP: %s, Path: %s. Cache hit\n", ip, path)
			c.Set(fiber.HeaderContentType, fiber.MIMEApplicationJSON)
			return c.SendString(cacheResponse)
		}

		// Marshal the updated request back to JSON
        updatedReqBody, err := json.Marshal(req)
        if err != nil {
            log.Printf("IP: %s, Path: %s. ERROR: Cannot marshal updated request body: %s\n", ip, path, err)
            return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
                "error": "Cannot marshal updated request body",
            })
        }

		resp, err := http.Post(forwardURL, "application/json", bytes.NewBuffer(updatedReqBody))
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

// 		// Cache the response
// 		err = rdb.Set(ctx, "response:"+cacheKey, body, 10*time.Minute).Err()
// 		if err != nil {
// 			log.Printf("IP: %s, Path: %s. ERROR: Cannot cache response: %s\n", ip, path, err)
// 		}

		log.Printf("IP: %s, Path: %s. Forwarded request successfully\n", ip, path)
		c.Set(fiber.HeaderContentType, fiber.MIMEApplicationJSON)
		return c.Send(body)
	})

	// Start the server on port 3000
	log.Printf("Starting server on port %s...", *port)
	log.Printf("Redis server %s:%s...", *redisHost, *redisPort)
	log.Printf("Forwarding destination %s:%s...", *fwdHost, *fwdPort)
	log.Fatal(app.Listen(fmt.Sprintf(":%s", *port)))
}
