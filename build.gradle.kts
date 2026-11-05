plugins {
    java
}

repositories {
    mavenLocal()
    mavenCentral()
}

fun prop(name: String): String? = providers.gradleProperty(name).orNull

val reqcoverVersion: String = prop("reqcoverVersion")!!

sourceSets.test {
    if (prop("noConfigFile") != "true") resources.srcDir("src/test/config")
}

dependencies {
    testImplementation(platform("org.junit:junit-bom:6.1.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testImplementation("org.junit.jupiter:junit-jupiter-params")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    testImplementation("dev.reqcover:reqcover-junit-jupiter:$reqcoverVersion")
    testRuntimeOnly("dev.reqcover:reqcover-source-openapi:$reqcoverVersion")
    if (prop("noReporters") != "true") {
        testRuntimeOnly("dev.reqcover:reqcover-reporter-html:$reqcoverVersion")
        testRuntimeOnly("dev.reqcover:reqcover-reporter-xml:$reqcoverVersion")
    }
}

val passThrough = mapOf(
    "requirementsUris" to "reqCover.requirementsUris",
    "legacyRequirementsUri" to "reqCover.requirementsUri",
    "reqCoverMin" to "reqCover.minimumRequiredCoveragePercent",
    "failIfBelowMinimum" to "reqCover.failIfBelowMinimum",
    "breakListBooks" to "ft.breakListBooks",
    "abortGetBook" to "ft.abortGetBook",
    "disableBlankTitle" to "ft.disableBlankTitle",
    "breakAllInvalidIsbn" to "ft.breakAllInvalidIsbn",
    "breakRepeated" to "ft.breakRepeated",
    "breakDynamic" to "ft.breakDynamic",
)

tasks.test {
    useJUnitPlatform {
        prop("excludeTags")?.let { excludeTags(*it.split(",").toTypedArray()) }
    }
    passThrough.forEach { (gradleName, systemName) -> prop(gradleName)?.let { systemProperty(systemName, it) } }
    outputs.upToDateWhen { false }
    testLogging {
        showStandardStreams = true
        events("passed", "failed", "skipped")
    }
}
