package vn.tetticket.architecture;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

@AnalyzeClasses(packages = "vn.tetticket", importOptions = ImportOption.DoNotIncludeTests.class)
public class ModularArchitectureTest {

    @ArchTest
    public static final ArchRule modules_should_be_free_of_cycles =
        slices().matching("vn.tetticket.(*)..")
            .should().beFreeOfCycles();

    @ArchTest
    public static final ArchRule shared_should_not_depend_on_feature_modules =
        noClasses().that().resideInAPackage("vn.tetticket.shared..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "vn.tetticket.identity..",
                "vn.tetticket.catalog..",
                "vn.tetticket.inventory..",
                "vn.tetticket.waitingroom..",
                "vn.tetticket.payment..",
                "vn.tetticket.ticketing..",
                "vn.tetticket.notification.."
            );

    @ArchTest
    public static final ArchRule identity_should_not_depend_on_order_flow_modules =
        noClasses().that().resideInAPackage("vn.tetticket.identity..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "vn.tetticket.inventory..",
                "vn.tetticket.waitingroom..",
                "vn.tetticket.payment..",
                "vn.tetticket.ticketing.."
            );
}
