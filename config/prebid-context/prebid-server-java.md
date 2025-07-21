# Prebid Server Java Technical Context

## Architecture: Spring Boot Application with Vert.x

Prebid Server Java is an alternative implementation of Prebid Server using Java, Spring Boot, and Vert.x for high-performance async operations.

### Core Differences from Go Version

While functionally equivalent to the Go version, the Java implementation has different patterns:

1. **Framework**: Spring Boot instead of raw HTTP handlers
2. **Async**: Vert.x for non-blocking I/O instead of goroutines  
3. **Configuration**: Spring application.yaml instead of custom YAML
4. **Dependency Injection**: Spring DI instead of manual wiring

### Adapter Implementation Pattern

```java
// src/main/java/org/prebid/server/bidder/example/ExampleBidder.java
@Component
public class ExampleBidder implements Bidder<BidRequest> {
    
    private final String endpointUrl;
    private final JacksonMapper mapper;
    
    public ExampleBidder(String endpointUrl, JacksonMapper mapper) {
        this.endpointUrl = HttpUtil.validateUrl(Objects.requireNonNull(endpointUrl));
        this.mapper = Objects.requireNonNull(mapper);
    }
    
    @Override
    public Result<List<HttpRequest<BidRequest>>> makeHttpRequests(BidRequest request) {
        final List<HttpRequest<BidRequest>> httpRequests = new ArrayList<>();
        
        for (Imp imp : request.getImp()) {
            final ExtImpExample extImp = parseImpExt(imp);
            if (extImp != null) {
                httpRequests.add(createRequest(imp, extImp));
            }
        }
        
        return Result.withValues(httpRequests);
    }
    
    @Override
    public Result<List<BidderBid>> makeBids(HttpCall<BidRequest> httpCall, BidRequest bidRequest) {
        try {
            final BidResponse bidResponse = mapper.decodeValue(
                httpCall.getResponse().getBody(), BidResponse.class);
            return Result.withValues(extractBids(bidResponse));
        } catch (DecodeException e) {
            return Result.withError(BidderError.badServerResponse(e.getMessage()));
        }
    }
}
```

### Configuration Structure

```yaml
# application.yaml
spring:
  main:
    banner-mode: "off"

vertx:
  worker-pool-size: 20
  event-loop-pool-size: 0  # 0 = 2 * CPU cores

http:
  port: 8080
  max-headers-size: 16384
  max-initial-line-length: 4096

auction:
  timeout-resolver:
    default: 200
    max: 5000
  
adapters:
  example:
    enabled: true
    endpoint: https://bid.example.com/prebid
    meta-info:
      maintainer-email: support@example.com
      vendor-id: 123
      
gdpr:
  enabled: true
  default-value: 1
  vendorlist:
    default-timeout-ms: 5000
    
metrics:
  prometheus:
    enabled: true
    port: 8081
    namespace: prebid
    subsystem: server
```

### Spring Boot Integration Points

```java
// Configuration class
@Configuration
@ConfigurationProperties(prefix = "adapters.example")
public class ExampleConfiguration {
    
    @NotBlank
    private String endpoint;
    
    @Bean
    BidderDeps exampleBidderDeps(ExampleConfiguration config, 
                                 JacksonMapper mapper) {
        return BidderDeps.of(
            new ExampleBidder(config.getEndpoint(), mapper),
            new ExampleMetaInfo()
        );
    }
}

// Meta info registration
@Component
public class ExampleMetaInfo implements BidderInfo {
    
    @Override
    public String getName() {
        return "example";
    }
    
    @Override
    public Set<MediaType> getSupportedMediaTypes() {
        return EnumSet.of(MediaType.banner, MediaType.video);
    }
}
```

### Vert.x Async Patterns

```java
// Async HTTP client usage
public class ExampleBidder implements Bidder<BidRequest> {
    
    @Override
    public Result<List<HttpRequest<BidRequest>>> makeHttpRequests(BidRequest request) {
        // Returns immediately, actual HTTP happens async
        return Result.withValues(
            Collections.singletonList(
                HttpRequest.<BidRequest>builder()
                    .method(HttpMethod.POST)
                    .uri(endpointUrl)
                    .headers(headers)
                    .payload(request)
                    .body(mapper.encodeToBytes(request))
                    .build()
            )
        );
    }
}

// Vert.x Future composition
public Future<AuctionContext> processAuction(AuctionContext context) {
    return fetchBids(context)
        .compose(this::validateBids)
        .compose(this::applyPriceFloors)
        .compose(this::cacheBids)
        .compose(this::buildResponse);
}
```

### Request/Response Enrichment

```java
// Hooks for request enrichment
@Component
public class ExampleRequestHook implements ProcessedAuctionRequestHook {
    
    @Override
    public Future<InvocationResult<AuctionRequestPayload>> call(
            AuctionRequestPayload payload,
            AuctionInvocationContext context) {
        
        final BidRequest bidRequest = payload.bidRequest();
        
        // Enrich with first-party data
        final BidRequest enriched = bidRequest.toBuilder()
            .ext(enrichExt(bidRequest.getExt()))
            .build();
            
        return Future.succeededFuture(
            InvocationResult.succeeded(payload.with(enriched))
        );
    }
}
```

### Testing Structure

```java
// src/test/java/org/prebid/server/bidder/example/ExampleBidderTest.java
public class ExampleBidderTest extends VertxTest {
    
    private ExampleBidder target;
    
    @Before
    public void setup() {
        target = new ExampleBidder("https://example.com", jacksonMapper);
    }
    
    @Test
    public void makeHttpRequestsShouldReturnExpectedRequest() {
        // given
        final BidRequest bidRequest = givenBidRequest(
            impBuilder -> impBuilder
                .ext(mapper.valueToTree(ExtPrebid.of(
                    null, ExtImpExample.of("placementId"))))
        );
        
        // when
        final Result<List<HttpRequest<BidRequest>>> result = 
            target.makeHttpRequests(bidRequest);
        
        // then
        assertThat(result.getErrors()).isEmpty();
        assertThat(result.getValue()).hasSize(1)
            .extracting(HttpRequest::getUri)
            .containsExactly("https://example.com");
    }
    
    @Test
    public void makeBidsShouldReturnExpectedBids() {
        // given
        final HttpCall<BidRequest> httpCall = givenHttpCall(
            givenBidResponse(bidBuilder -> bidBuilder.impid("123"))
        );
        
        // when
        final Result<List<BidderBid>> result = 
            target.makeBids(httpCall, BidRequest.builder().build());
        
        // then
        assertThat(result.getValue())
            .extracting(BidderBid::getBid)
            .extracting(Bid::getImpid)
            .containsExactly("123");
    }
}
```

### Key Differences in PR Patterns

**Java-specific patterns to look for:**

1. **Spring Annotations**: `@Component`, `@Configuration`, `@Bean`
2. **Lombok Usage**: `@Builder`, `@Value`, `@AllArgsConstructor`
3. **Vert.x Futures**: Async operations return `Future<T>`
4. **Jackson Mapping**: JSON handled via `JacksonMapper`
5. **Validation**: Bean validation annotations like `@NotNull`, `@Valid`

**File Structure for New Adapters:**
```
src/main/java/org/prebid/server/
├── bidder/example/
│   ├── ExampleBidder.java         # Main bidder implementation
│   ├── ExampleMetaInfo.java       # Bidder metadata
│   └── proto/                     # Request/response models
├── spring/config/bidder/
│   └── ExampleConfiguration.java  # Spring configuration
└── resources/bidder-config/
    └── example.yaml               # Static configuration

src/test/java/org/prebid/server/
└── bidder/example/
    └── ExampleBidderTest.java     # Unit tests
```

### Performance Considerations

The Java version uses:
- **Netty**: For high-performance networking
- **Vert.x**: For event loop and async operations
- **Jackson**: For JSON processing with custom optimizations
- **Caffeine**: For caching instead of Go's sync.Map

### Module System

Java version uses a different module system:

```java
// Modules implement specific interfaces
public interface Module {
    // Hook interfaces
    interface RawAuctionRequestHook {}
    interface ProcessedAuctionRequestHook {}
    interface BidderRequestHook {}
    interface RawBidderResponseHook {}
    interface AllProcessedBidResponsesHook {}
    interface AuctionResponseHook {}
}

// Registration via Spring
@Configuration
@ConditionalOnProperty(prefix = "hooks.modules.example", name = "enabled", havingValue = "true")
public class ExampleModuleConfiguration {
    
    @Bean
    ExampleModule exampleModule() {
        return new ExampleModule();
    }
}
```