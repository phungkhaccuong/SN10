package main

import (
	"flag"
	"fmt"
	"log"

	"github.com/gofiber/fiber/v2"
)

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
	port := flag.String("port", "3000", "Port to run the Fiber app on")

	// Parse the command-line flags
	flag.Parse()

	// Create a new Fiber instance
	app := fiber.New()

	// Define a POST route to handle JSON requests
	app.Post("/AllocateAssets", func(c *fiber.Ctx) error {
		ip := c.IP()
		path := c.Path()
		log.Printf("IP: %s, Path: %s\n", ip, path)

		// Parse the JSON request body into the User struct
		req := new(InputRequest)
		if err := c.BodyParser(req); err != nil {
			log.Printf("IP: %s, Path: %s. ERROR: Cannot parse JSON from body: %s\n", ip, path, c.Body())
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Cannot parse JSON",
			})
		}

		// Construct the response
		res := FinalResponse{}
		res.AssetsAndPools.TotalAssets = req.AssetsAndPools.TotalAssets
		res.AssetsAndPools.Pools = req.AssetsAndPools.Pools
		res.Allocations = map[string]float64{}
		for key, value := range req.AssetsAndPools.Pools {
			res.Allocations[key] = value.BorrowAmount
		}
		res.Name = "AllocateAssets"

		log.Printf("IP: %s, Path: %s. Response with status %d\n", ip, path, fiber.StatusOK)
		// Respond with the received JSON data
		return c.JSON(res)
	})

	// Start the server on port 3000
	log.Printf("Starting server on port %s...", *port)
	log.Fatal(app.Listen(fmt.Sprintf(":%s", *port)))
}
