package main

/*
#cgo pkg-config: python3
#include <Python.h>
#include <stdlib.h>
*/
import "C"
import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"sync"
	"unsafe"

	"github.com/gofiber/fiber/v2"
)

// initPython initializes the Python interpreter and imports the module
func initPython() {
	C.Py_Initialize()

	pyModuleName := C.CString("script")
	pyModule = C.PyImport_ImportModule(pyModuleName)
	C.free(unsafe.Pointer(pyModuleName))

	if pyModule == nil {
		fmt.Println("Error importing Python module")
		C.Py_Finalize()
	}
}

func add(a, b int) int {
	// Ensure the Python interpreter and module are initialized only once
	once.Do(initPython)

	if pyModule == nil {
		fmt.Println("Python module not initialized")
		return 0
	}

	// Get the add function from the module
	pyFuncName := C.CString("add")
	pyFunc := C.PyObject_GetAttrString(pyModule, pyFuncName)
	C.free(unsafe.Pointer(pyFuncName))

	if pyFunc == nil || !C.PyCallable_Check(pyFunc) {
		fmt.Println("Error getting Python function")
		return 0
	}

	// Call the add function with arguments
	args := C.PyTuple_New(2)
	C.PyTuple_SetItem(args, 0, C.PyLong_FromLong(C.long(a)))
	C.PyTuple_SetItem(args, 1, C.PyLong_FromLong(C.long(b)))

	result := C.PyObject_CallObject(pyFunc, args)
	if result != nil {
		res := int(C.PyLong_AsLong(result))
		C.Py_DECREF(result)
		C.Py_DECREF(args)
		C.Py_DECREF(pyFunc)
		return res
	} else {
		fmt.Println("Error calling Python function")
		C.Py_DECREF(args)
		C.Py_DECREF(pyFunc)
		return 0
	}
}

func handler(w http.ResponseWriter, r *http.Request) {
	a, err1 := strconv.Atoi(r.URL.Query().Get("a"))
	b, err2 := strconv.Atoi(r.URL.Query().Get("b"))
	if err1 != nil || err2 != nil {
		http.Error(w, "Invalid parameters", http.StatusBadRequest)
		return
	}

	result := add(a, b)
	fmt.Fprintf(w, "Result: %d\n", result)
}

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

var (
	pyModule *C.PyObject
	once     sync.Once
)

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

	app.Get("/add", func(c *fiber.Ctx) error {
		a, err1 := strconv.Atoi(c.Query("a"))
		b, err2 := strconv.Atoi(c.Query("b"))
		if err1 != nil || err2 != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid parameters")
		}

		result := add(a, b)
		return c.SendString(fmt.Sprintf("Result: %d\n", result))
	})

	// Start the server on port 3000
	log.Printf("Starting server on port %s...", *port)
	log.Fatal(app.Listen(fmt.Sprintf(":%s", *port)))
}
