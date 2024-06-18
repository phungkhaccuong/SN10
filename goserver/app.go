package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"runtime"
	"time"
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

type AssetRequest struct {
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
	// Set GOMAXPROCS to the number of CPUs available
	runtime.GOMAXPROCS(runtime.NumCPU())

	// Create a custom server with timeouts for better performance under load
	server := &http.Server{
		Addr:           ":8080",
		Handler:        http.DefaultServeMux,
		ReadTimeout:    10 * time.Second,
		WriteTimeout:   10 * time.Second,
		MaxHeaderBytes: 1 << 20, // 1 MB
	}

	http.HandleFunc("/AllocateAssets", postHandler)
	http.HandleFunc("/GET", getHandler)

	fmt.Println("Server is running on port 8080")
	log.Fatal(server.ListenAndServe())
}

func getHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Println("Received GET request: %s", r.URL.Path)
	// Check if the request method is GET
	if r.Method != http.MethodGet {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}
	// Set the Content-Type header
	w.Header().Set("Content-Type", "application/json")
	// Write the response
	w.Write([]byte("GET request received"))
	return
}

func postHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Println("Received POST request", r.RemoteAddr, r.URL.Path)
	// Check if the request method is POST
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		fmt.Println("ERROR: Invalid request method %s", http.StatusMethodNotAllowed)
		return
	}
	// Read the body of the request
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Error reading request body", http.StatusInternalServerError)
		fmt.Println("ERROR: Error reading request body %s", err)
		return
	}
	defer r.Body.Close()

	var req AssetRequest
	err = json.Unmarshal(body, &req)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusInternalServerError)
		fmt.Println("ERROR: Error parsing JSON %s", err)
		return
	}

	res := FinalResponse{}
	res.AssetsAndPools.TotalAssets = req.AssetsAndPools.TotalAssets
	res.AssetsAndPools.Pools = req.AssetsAndPools.Pools
	res.Allocations = map[string]float64{}
	for key, value := range req.AssetsAndPools.Pools {
		res.Allocations[key] = value.BorrowAmount
	}
	res.Name = "AllocateAssets"

	// Marshal the final response back to JSON
	responseJSON, err := json.Marshal(res)
	if err != nil {
		fmt.Println("Error marshaling final response:", err)
		fmt.Println("ERROR: Error Error marshaling final response %s", err)
		return
	}

	// Print the final JSON response
	// fmt.Println(string(responseJSON))

	// Set the Content-Type header
	w.Header().Set("Content-Type", "application/json")
	// w.Write([]byte(responseJSON))
	w.Write(responseJSON)
	return
}
